# SKILLS.md

Step-by-step recipes for the most common development tasks in K9-AIF.
Read alongside `CLAUDE.md` (architecture) — this file covers *how to build*, not *how it works*.

---

## Skill 1 — Add a new Agent

### Step 1: Create the agent YAML

```
examples/<App>/agents/yaml/my_agent.yaml
```

```yaml
name: MyAgent
class: MyAgent                         # must match the Python class name exactly

description: >
  What this agent does in one paragraph.

pattern: reasoning                     # reasoning | extraction | chat | guardrails
model: reasoning                       # must match a key in inference.model_catalog

role: >
  You are a ... (LLM system prompt — who the agent is)

goal: >
  Your goal is to ... (what the agent must achieve)

instructions:
  - Instruction one
  - Instruction two
  - Always include confidence score in output

output_schema:
  field_one: string
  field_two: float
  confidence: float (0.0–1.0)

tools: []

governance:
  pre_process: true
  post_process: false

# Optional — 4Ds AI Fluency annotations (see Skill 12)
delegation:
  interaction_mode: automation       # automation | augmentation | agency
  ai_tasks: [classify, score]
  human_tasks: [approve, override]
```

### Step 2: Create the Python class

```
examples/<App>/agents/src/my_agent.py
```

```python
from typing import Any, Dict, Optional
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke


class MyAgent(BaseAgent):

    layer = "<App> MyAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Build prompt from payload + agent YAML config
        prompt = (
            f"Role: {self.config.get('role', '')}\n"
            f"Goal: {self.config.get('goal', '')}\n\n"
            f"Input: {payload}"
        )

        # 2. Build InferenceRequest — task_type drives model scoring
        req = InferenceRequest(
            prompt=prompt,
            task_type=self.config.get("model", "general"),
            metadata={"agent": "MyAgent"},
        )

        # 3. Invoke LLM via router
        resp = llm_invoke(self.config, req)

        # 4. Return structured result
        result = {
            "agent": "MyAgent",
            "output": resp.output.strip(),
            "model_used": resp.model_alias,
        }

        # 5. Publish event for audit trail
        self.publish_event({"type": "MyAgentCompleted", "agent": "MyAgent"})

        return result
```

### Step 3: Register in `_load_squad()`

Agents are not registered with the orchestrator — they are registered into `AgentRegistry` inside `_load_squad()` so `SquadLoader` can wire them into the Squad. The orchestrator only holds the assembled Squad.

```python
from examples.<App>.agents.src.my_agent import MyAgent

for name, cls in [
    ...
    ("MyAgent", MyAgent),          # add here
]:
    agent_registry.register(
        name,
        lambda c=cls, n=name: c(config=agent_loader.merge_with_global(n, self.config)),
    )
```

### Step 4: Add to the squad YAML flow

Each `flow:` step must be a dict with an `agent:` key — plain strings will raise `ValueError` at runtime.

**Decoupling rule:** Squad YAML knows only its own agents and flow. It does NOT reference orchestrators — the orchestrator is the caller; the squad must not know its caller.

```yaml
# config/squads.yaml  (note the squads: wrapper and squad ID key)
squads:
  MySquad:
    description: "What this squad does."
    agents:
      - ...
      - MyAgent
    flow:
      - ...
      - agent: MyAgent
        result_key: my_agent        # key under which result is stored in context
```

Optional flow step fields: `result_key` (defaults to agent name), `context` (static overrides merged into step input), `when` (condition — step skipped if false).

---

## Skill 2 — How an Agent invokes the LLM

This is the complete chain every agent must follow. Never call `OllamaLLM` or `LLMFactory` directly from agent code.

```python
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke   # ABB — use this by default

# 1. Build the request
req = InferenceRequest(
    prompt="Your prompt here",
    task_type="reasoning",           # drives K9ModelRouter scoring (+3 for capability match)
    sensitivity="confidential",      # optional — routes to guardian model (+2)
    latency_budget="realtime",       # optional — boosts realtime-tier models (+2)
    cost_profile="minimal",          # optional — boosts minimal-cost models (+2)
    metadata={"agent": "MyAgent", "correlation_id": correlation_id},
)

# 2. Invoke — ModelRouterFactory selects the right model, persists the decision
resp = llm_invoke(self.config, req)

# 3. Check the response
resp.output        # the LLM text output
resp.model_alias   # which model was selected (e.g. "reasoning")
resp.provider      # e.g. "ollama"
resp.latency_ms    # round-trip time
```

**What happens under the hood:**

```
llm_invoke(config, req)
  → ModelRouterFactory.get_router(config)      # cached router instance
  → K9ModelRouter.route(req)                   # scores all catalog models
  → catalog.get_model(best_alias)              # looks up llm_ref
  → LLMFactory.get(llm_ref)                   # cached OllamaLLM instance
  → OllamaLLM.invoke(prompt)                  # hits Ollama at ${OLLAMA_BASE_URL}
  → RouteDecision + complexity/governance scores persisted to routing state store (SQLite or PostgreSQL)
```

**If the LLM is unreachable**, `llm_invoke` raises `RuntimeError` — it never silently returns empty output. Handle it:

```python
try:
    resp = llm_invoke(self.config, req)
except RuntimeError as exc:
    self.logger.error("[%s] LLM unavailable: %s", self.layer, exc)
    return {"agent": "MyAgent", "output": "[WARN] LLM unavailable", "confidence": 0.0}
```

---

## Skill 3 — How to add a custom Model Router by extending BaseModelRouter

The ABB contract is `BaseModelRouter` (`k9_aif_abb/k9_inference/routers/base_model_router.py`).
It defines **three** abstract methods: `route()`, `invoke()`, and `ainvoke()` (async) — all three must be implemented.

`K9ModelRouter` is the **OOB default SBB** — a ready-to-use extension that scores models from the catalog using weighted signals. `DefaultModelRouter` is a second OOB option (`router.type: default`). Neither is mandatory.

If a solution needs different routing logic (cost optimization, compliance routing, A/B testing, provider switching), extend `BaseModelRouter` and register it via config. The rest of the framework — agents, squads, orchestrators — is unaffected.

### Step 1: Extend `BaseModelRouter`

```python
# examples/<App>/routers/my_router.py

from k9_aif_abb.k9_inference.routers.base_model_router import BaseModelRouter
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_inference.models.inference_response import InferenceResponse
from k9_aif_abb.k9_inference.models.route_decision import RouteDecision
from k9_aif_abb.k9_factories.llm_factory import LLMFactory


class MyRouter(BaseModelRouter):

    def route(self, request: InferenceRequest) -> RouteDecision:
        alias = "reasoning" if request.task_type == "reasoning" else "general"
        return RouteDecision(model_alias=alias)

    def invoke(self, request: InferenceRequest) -> InferenceResponse:
        decision = self.route(request)
        llm = LLMFactory.get(decision.model_alias)
        return llm.invoke(request.prompt)

    async def ainvoke(self, request: InferenceRequest) -> InferenceResponse:
        decision = self.route(request)
        llm = LLMFactory.get(decision.model_alias)
        return await llm.ainvoke(request.prompt)
```

### Step 2: Register in `config.yaml`

```yaml
inference:

  # Declare your router — replaces K9ModelRouter
  router:
    type: my_router                   # registered name of your BaseModelRouter implementation
    default_model: general
    persistence:
      enabled: true
      provider: sqlite                # sqlite | postgres | memory

  # LLMFactory — Ollama model name and parameters
  llm_factory:
    models:
      general:
        model: "llama3.2:1b"
        temperature: 0.3
        max_tokens: 2048
      reasoning:
        model: "granite3-dense:2b"
        temperature: 0.2
        max_tokens: 4096

  # Model catalog — available to any router for alias → capability mapping
  model_catalog:
    models:
      general:
        provider: ollama
        llm_ref: general
        capabilities: [general, chat, summarization]
        latency_tier: realtime
        cost_tier: minimal
      reasoning:
        provider: ollama
        llm_ref: reasoning
        capabilities: [reasoning, analysis, extraction]
        latency_tier: interactive
        cost_tier: standard
```

### Using the OOB K9ModelRouter (no code needed)

If `K9ModelRouter` is sufficient — keep `type: k9_model_router` in config and only define the catalog entries. The router scores models automatically using `InferenceRequest` signals (`task_type`, `sensitivity`, `latency_budget`, `cost_profile`). No Python code required.

---

## Skill 4 — Add a new Squad

### Decoupling principle — three independent layers

Each layer in the execution hierarchy knows only what is **below** it. Nothing references its caller.

| Layer | Knows about | Does NOT know about |
|---|---|---|
| **Orchestrator** | Its squad ID (loads it via `_load_squad()`) | Routers, other orchestrators |
| **Squad** | Its agents and flow steps | Orchestrators |
| **Agent** | Its own behavior (role, goal, model) | Squads, routing, next agent |

This means:
- Squad YAML has **no** `orchestrator:` field — the orchestrator is the caller, not a peer
- Agent YAML has **no** `squad:` or `routing:` fields — agents are squad-agnostic, reusable across squads

### Squad YAML

```
examples/<App>/config/squads.yaml
```

`SquadLoader` reads `data["squads"]` — the squad ID is a key under `squads:`, not a `name:` field. Flow steps **must** be dicts with an `agent:` key. Plain strings will raise `ValueError`.

```yaml
squads:
  MySquad:
    description: "What this squad does."
    agents:
      - AgentOne
      - AgentTwo
      - AuditAgent
    flow:
      - agent: AgentOne
        result_key: agent_one
      - agent: AgentTwo
        result_key: agent_two
      - agent: AuditAgent
        result_key: audit
```

### Agent YAML

Agent YAML describes behavior only — no squad references, no routing fields.

```yaml
name: AgentOne
class: AgentOne

description: >
  What this agent does.

pattern: reasoning
model: reasoning

role: >
  You are a ...

goal: >
  Your goal is to ...

instructions:
  - Instruction one

output_schema:
  result: string
  confidence: float

governance:
  pre_process: true
  post_process: false
```

### Wire it in `_load_squad()`

```python
loader = SquadLoader(agent_registry)
squad = loader.load_one(squads_yaml_path, "MySquad")
```

---

## Skill 5 — Governance enforcement in an Agent

`K9_ENV` controls what happens when `enforce_governance()` is called:

| `K9_ENV` | `enforce_governance()` behaviour |
|---|---|
| `development` / `test` | Logs WARNING, continues |
| `production` / `staging` | Raises `PermissionError` — agent stops |

**To require governance before executing:**

```python
def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        self.enforce_governance()        # raises in production if NoopGovernance
    except PermissionError as exc:
        self.logger.error("[%s] %s", self.layer, exc)
        return {"agent": self.layer, "output": "[WARN] governance not configured"}

    # ... rest of execute
```

**To apply governance pipeline hooks:**

```python
import asyncio

# Pre-process (sanitize/validate input before LLM)
payload = asyncio.get_event_loop().run_until_complete(
    self.apply_pre_governance(payload)
)

# ... call llm_invoke ...

# Post-process (validate/redact output after LLM)
result = asyncio.get_event_loop().run_until_complete(
    self.apply_post_governance(result)
)
```

---

## Skill 6 — Write a test for an Agent

No LLM or database needed — mock `llm_invoke` and test `execute()` directly.

```python
from unittest.mock import patch, MagicMock
from examples.<App>.agents.src.my_agent import MyAgent
from k9_aif_abb.k9_inference.models.inference_response import InferenceResponse


class _TestGovernance:
    """Minimal concrete governance for tests — define inline, not imported."""
    def pre_process(self, payload: dict, ctx=None) -> dict:
        return payload
    def post_process(self, payload: dict, ctx=None) -> dict:
        return payload

def _make_agent(config=None):
    return MyAgent(config=config or {}, governance=_TestGovernance())


def test_execute_returns_output():
    mock_resp = MagicMock(spec=InferenceResponse)
    mock_resp.output = "Assessment complete."
    mock_resp.model_alias = "reasoning"
    mock_resp.provider = "ollama"

    with patch("examples.<App>.agents.src.my_agent.llm_invoke", return_value=mock_resp):
        agent = _make_agent()
        result = agent.execute({"claim_id": "C001", "amount": 5000})

    assert result["agent"] == "MyAgent"
    assert "output" in result


def test_execute_handles_llm_unavailable():
    with patch("examples.<App>.agents.src.my_agent.llm_invoke",
               side_effect=RuntimeError("LLM backend unavailable")):
        agent = _make_agent()
        result = agent.execute({"claim_id": "C001"})

    assert "[WARN]" in result["output"]
```

---

## Skill 7 — Event publishing — Router and Orchestrator only

`publish_event()` is defined on `BaseAgent` and will publish to Kafka if a `message_bus` is passed at construction. By convention in K9-AIF solutions, **only the Router and Orchestrator are wired with a message bus** — agents are constructed without one.

Agents within a Squad share data sequentially through the flow — each agent's output enriches the shared execution context, which is passed as the input to the next agent. The context grows progressively richer as it moves through the flow. There is no need for Agent-to-Agent (A2A) messaging over Kafka. Agents use `self.logger` for observability.

A2A via Kafka is architecturally possible — wire an agent with a `message_bus` at construction and `publish_event()` will publish to a Kafka topic. This is not used in standard K9-AIF solutions but is a valid extension for rare scenarios requiring loosely coupled or async agent handoffs across squads.

### Kafka event topology

```
app_backend → eoc-events → [IntentAgent] → Router (publishes) → eoc-claims / eoc-fraud / …
                                                                          ↓
                                                          Orchestrator (consumes, runs squads)
                                                                          ↓
                                                          Orchestrator (publishes) → another Orchestrator (if chained)
                                                                          ↓
                                                                      eoc-results
```

| Component | Kafka role |
|---|---|
| **app_backend** | Publishes inbound events to the entry topic |
| **IntentAgent** _(optional)_ | Pre-routing LLM-based intent classification for non-deterministic inputs — stamps `intent` on the payload before the Router receives it. Supported in the ABB (`k9_aif_abb/k9_agents/router/router_agent.py`) |
| **Router** | Resolves the target domain topic dynamically — deterministic (`event_type` → topic) or intent-driven (`intent` → orchestrator). The topic it publishes to varies per event |
| **Orchestrator** | Consumes from domain topics; publishes results — or triggers another Orchestrator via a downstream topic |
| **Agents** | No Kafka access — observability via `self.logger` only |

### Router — publishing a domain event

`publish_event()` is called on the Router after routing decision is made:

```python
# Inside a Router subclass (extends BaseRouter)
self.publish_event({
    "type": "ClaimRouted",
    "event_type": event.get("event_type"),
    "topic": resolved_topic,
    "correlation_id": event.get("correlation_id"),
})
```

### Orchestrator — publishing a result event

```python
# Inside an Orchestrator subclass (extends BaseOrchestrator)
self.publish_event({
    "type": "FlowCompleted",
    "squad_id": _SQUAD_ID,
    "correlation_id": payload.get("correlation_id"),
    "result_summary": result.get("status"),
})
```

---

## Skill 8 — Add a new scoring signal to the Router

This applies to `K9ModelRouter` (the OOB default). If a solution has implemented a custom `BaseModelRouter`, extend that instead.

The scoring logic lives in `k9_aif_abb/k9_inference/routers/k9_model_router.py` — `_score_candidate()`.

To add a new signal (e.g. `+2` for environment match):

```python
def _score_candidate(self, alias: str, meta: dict, request: InferenceRequest) -> float:
    score = 0.0
    caps = meta.get("capabilities", [])

    if request.task_type and request.task_type in caps:
        score += 3.0

    if getattr(request, "sensitivity", None) == "confidential" and "confidential" in caps:
        score += 2.0

    if request.latency_budget and request.latency_budget == meta.get("latency_tier"):
        score += 2.0

    if request.cost_profile and request.cost_profile == meta.get("cost_tier"):
        score += 2.0

    # New signal — environment match
    if request.environment and request.environment == meta.get("environment_tier"):
        score += 2.0

    return score
```

Then add the field to `InferenceRequest` (Optional, default None — backwards compatible):

```python
environment: Optional[str] = None   # "local" | "cloud" | "air-gapped"
```

And add `environment_tier` to catalog entries in `config.yaml`.

---

## Skill 9 — Agent config: what comes from YAML vs global config

When `_load_squad()` constructs an agent it calls:

```python
agent_loader.merge_with_global("MyAgent", self.config)
```

This produces one merged dict passed as `agent.config`. Merge rule: **agent YAML wins on key collision**.

| Source | What it provides |
|---|---|
| `config.yaml` (global) | `inference`, `messaging`, `postgres`, `neo4j`, `governance`, `eoc` — infrastructure |
| `agent.yaml` | `role`, `goal`, `instructions`, `model`, `pattern`, `routing`, `governance.pre_process` — behavior |

So in an agent:

```python
self.config.get("role")           # from agent YAML
self.config.get("model")          # from agent YAML — e.g. "reasoning"
self.config.get("inference")      # from global config.yaml — full inference block
self.config.get("postgres")       # from global config.yaml — DB connection
```

This is why agents never hardcode prompts or model names — all behavior is in YAML, all infrastructure is in the global config.

---

## Skill 10 — Build an iterative validation agent using BaseValidationLoopAgent

`BaseValidationLoopAgent` (`k9_aif_abb/k9_agents/validation/`) is an ABB that provides a reusable **hypothesis → tool/test → observation → re-reason → continue or finalize** loop skeleton.

It generalises the pattern used by Aardvark-style systems across any domain — security, fraud, claims, compliance, document extraction — without containing domain logic itself.

### Why it exists

A standard `BaseAgent.execute()` is one-shot: payload in, result out. Some problems require iterative convergence — the agent must test a hypothesis, observe the outcome, update its understanding, and decide whether to try again. `BaseValidationLoopAgent` provides that skeleton so every solution team does not reinvent it.

### Loop lifecycle

```
execute(payload)
  → generate_hypothesis()        form the next thing to test
  → run_validation()             invoke tool / function / rule engine / LLM
  → evaluate_observation()       interpret raw result; return dict with confidence
  → should_continue()            return CONTINUE | FINALIZE | ESCALATE | FAIL
  → record ValidationLoopStep
  → repeat or terminate
```

### Step 1: Extend BaseValidationLoopAgent

```python
from k9_aif_abb.k9_agents.validation import (
    BaseValidationLoopAgent,
    ValidationDisposition,
    ValidationLoopContext,
    ValidationLoopResult,
)


class ClaimsEvidenceAgent(BaseValidationLoopAgent):

    layer = "ClaimsEvidenceAgent SBB"

    def generate_hypothesis(self, loop_ctx: ValidationLoopContext):
        # Use prior steps + payload to form the next evidence query
        return {"query": "policy_coverage", "claim_id": loop_ctx.payload["claim_id"]}

    def run_validation(self, hypothesis, loop_ctx: ValidationLoopContext):
        # Call your rule engine, database, or LLM here
        return my_policy_engine.check(hypothesis)

    def evaluate_observation(self, tool_result, loop_ctx: ValidationLoopContext):
        confidence = tool_result.get("match_score", 0.0)
        return {"covered": tool_result.get("covered"), "confidence": confidence}

    def should_continue(self, observation, loop_ctx: ValidationLoopContext):
        threshold = self.config.get("confidence_threshold", 0.8)
        if observation["confidence"] >= threshold:
            return ValidationDisposition.FINALIZE
        if loop_ctx.iteration >= 3 and observation["confidence"] < 0.4:
            return ValidationDisposition.ESCALATE
        return ValidationDisposition.CONTINUE

    def finalize(self, loop_ctx: ValidationLoopContext) -> ValidationLoopResult:
        last = loop_ctx.steps[-1]
        return ValidationLoopResult(
            disposition      = ValidationDisposition.FINALIZE,
            output           = {"decision": "approved", "confidence": last.confidence},
            steps            = loop_ctx.steps,
            iterations       = loop_ctx.iteration,
            final_confidence = last.confidence,
            evidence         = [str(s.observation) for s in loop_ctx.steps],
        )
```

### Step 2: Config YAML

```yaml
# In agent YAML or merged via config.yaml
max_iterations:             5      # hard cap on loop iterations
confidence_threshold:       0.8    # available to should_continue() via self.config
finalize_on_max_iterations: true   # true → finalize; false → escalate on timeout
```

### Dispositions

| Disposition | Meaning | Default handler |
|---|---|---|
| `CONTINUE` | Run another iteration | _(loop continues)_ |
| `FINALIZE` | Confidence sufficient — produce output | `finalize()` — **must override** |
| `ESCALATE` | Unresolvable — route to HIL | `escalate()` — override for domain HIL |
| `FAIL` | Definitive negative | `fail()` — override for domain failure output |

### What `models/` contains

`k9_agents/validation/models/validation_loop.py` holds the **state contracts** only — `ValidationLoopContext`, `ValidationLoopStep`, `ValidationLoopResult`, `ValidationDisposition`. No execution logic. This separation means loop state can be persisted, inspected by the orchestrator, fed into telemetry, or written to a Neo4j lineage graph without touching the agent implementation.

### Telemetry hooks emitted

`loop_started` · `hypothesis_generated` · `validation_tool_invoked` · `observation_evaluated` · `loop_continued` · `loop_finalized` · `loop_escalated` · `loop_failed`

All go through `publish_event()` — wired to monitor + message_bus if configured.

### OOB implementation — K9ValidationLoopAgent

`K9ValidationLoopAgent` is the ready-to-run OOB implementation, analogous to `K9ModelRouter` for routing. The LLM is the validation tool — no custom code required for the common case.

```python
from k9_aif_abb.k9_agents.validation import K9ValidationLoopAgent, ValidationDisposition

# Use OOB as-is — wire via agent YAML (class: K9ValidationLoopAgent)

# Or extend and override only what differs:
class FraudValidationAgent(K9ValidationLoopAgent):
    layer = "FraudValidationAgent SBB"

    def run_validation(self, hypothesis, loop_ctx):
        return fraud_rule_engine.evaluate(loop_ctx.payload)   # swap in domain tool

    def should_continue(self, observation, loop_ctx):
        if observation["confidence"] >= 0.9:
            return ValidationDisposition.FINALIZE
        if observation["confidence"] < 0.2:
            return ValidationDisposition.FAIL
        return ValidationDisposition.CONTINUE
```

Inheritance hierarchy:
```
BaseAgent
  └── BaseValidationLoopAgent   (loop skeleton — ABB)
        ├── K9ValidationLoopAgent   (LLM-driven OOB — confidence convergence)
        │     └── FraudValidationAgent   (domain SBB — overrides only what differs)
        └── K9PlanningLoopAgent    (LLM-driven OOB — dynamic plan + scratchpad)
```

### OOB implementation — K9PlanningLoopAgent

`K9PlanningLoopAgent` (`k9_aif_abb/k9_agents/planning/`) is the dynamic-planning sibling of `K9ValidationLoopAgent`. Same loop skeleton, same "LLM is the validation tool" approach — the difference is the loop-continuation signal.

Each iteration, the LLM is shown its current plan (`remaining_steps`) and scratchpad (`notes`), carried across iterations in `ValidationLoopContext`. It returns an updated plan and notes alongside the usual `confidence`/`reasoning`. The loop `FINALIZE`s when the LLM explicitly returns an empty `remaining_steps` (plan complete) **or** `confidence` reaches `confidence_threshold` — whichever comes first. If the LLM's response can't be parsed, or it doesn't mention a plan, behaviour falls back to confidence-driven continuation exactly like `K9ValidationLoopAgent`.

```python
from k9_aif_abb.k9_agents.planning import K9PlanningLoopAgent

# Use OOB as-is — wire via agent YAML (class: K9PlanningLoopAgent)

# Or extend and override only what differs (e.g. fail fast on very low confidence
# regardless of plan state):
class StrictPlanningAgent(K9PlanningLoopAgent):
    layer = "StrictPlanningAgent SBB"

    def should_continue(self, observation, loop_ctx):
        if observation["confidence"] < 0.2:
            return ValidationDisposition.FAIL
        return super().should_continue(observation, loop_ctx)
```

Config keys are the same as `K9ValidationLoopAgent` (`role`, `goal`, `model`, `max_iterations`, `confidence_threshold`, `finalize_on_max_iterations`, `escalate_on_tool_error`) — no new YAML keys are required. `remaining_steps`/`notes` are runtime state, not config.

`_to_dict()` output includes two additional top-level keys for **every** `BaseValidationLoopAgent` subclass (additive — existing agents simply report empty defaults):

| Key | Type | Meaning |
|---|---|---|
| `remaining_steps` | `list[str]` | Final plan state at finalize time (empty if complete or unused) |
| `notes` | `dict` | Final scratchpad state at finalize time (empty if unused) |

### Solutions Architect decision — BaseAgent vs K9ValidationLoopAgent vs K9PlanningLoopAgent

> **The generator, intake, and Claude Code scaffold all agents extending `BaseAgent` by default.** This is correct for most agents. The SA must explicitly decide at design time which agents need a loop, and which loop variant.

Ask this question for every agent during design:

> *"Does this agent need to test something, observe the result, and decide whether to try again — or does it produce its answer in one pass? If it loops, is the number of steps known in advance (convergence on a confidence score), or does the agent need to plan and revise its own steps as it goes?"*

| Answer | Extend |
|---|---|
| One-pass — classify, route, audit, guard, sync | `BaseAgent` |
| Iterative convergence on a confidence score — fraud, evidence, compliance, document confidence | `K9ValidationLoopAgent` |
| Open-ended — agent must plan its own steps and revise the plan as it learns — investigation, diagnosis, multi-stage research | `K9PlanningLoopAgent` |

When changing a generated agent from one-shot to iterative, replace the parent class and swap `execute()` for the five loop methods:

| Remove | Add |
|---|---|
| `class MyAgent(BaseAgent)` | `class MyAgent(K9ValidationLoopAgent)` |
| `def execute(self, payload)` | `def generate_hypothesis(self, loop_ctx)` |
| | `def run_validation(self, hypothesis, loop_ctx)` |
| | `def evaluate_observation(self, tool_result, loop_ctx)` |
| | `def should_continue(self, observation, loop_ctx)` |
| | `def finalize(self, loop_ctx) -> ValidationLoopResult` |

**EOC reference agents already migrated (use as examples):**
- `FraudDetectionAgent` (`examples/.../agents/src/fraud_detection_agent.py`) — extends `K9ValidationLoopAgent`; fraud signal correlation across multiple passes
- `DocumentExtractorAgent` (`examples/.../agents/src/document_extractor_agent.py`) — extends `K9ValidationLoopAgent`; extraction confidence check + re-extraction on parse failure

---

## Skill 11 — Provider Adapter Pattern (Secret Management, Cache, and future areas)

The multi-provider LLM pattern is applied consistently to all infrastructure concerns. Every area follows the same three-layer structure: **ABB contract** → **provider adapters** → **static factory**.

### Structure

```
k9_core/<concern>/base_<concern>.py     ← ABB abstract contract (EXTENDS nothing)
k9_<concern>/adapters/<name>_adapter.py ← Concrete implementations (EXTENDS contract)
k9_factories/<concern>_factory.py       ← Static factory (register / get / create)
```

### Step 1: Define the ABB contract

```python
# k9_core/<concern>/base_<concern>.py
from abc import ABC, abstractmethod

class BaseMyThing(ABC):
    @abstractmethod
    def do_thing(self, key: str) -> str:
        raise NotImplementedError

    # Optional override with default implementation
    def exists(self, key: str) -> bool:
        try:
            self.do_thing(key)
            return True
        except KeyError:
            return False
```

### Step 2: Implement adapters

Default adapter (zero dependencies, always works):

```python
# k9_<concern>/adapters/default_adapter.py
from k9_aif_abb.k9_core.<concern>.base_<concern> import BaseMyThing

class DefaultMyThingAdapter(BaseMyThing):
    def __init__(self, config=None):
        self._config = config or {}

    def do_thing(self, key: str) -> str:
        ...
```

Optional-dependency adapter (lazy import pattern — mandatory for all heavy adapters):

```python
# k9_<concern>/adapters/heavy_adapter.py
class HeavyMyThingAdapter(BaseMyThing):
    def __init__(self, config=None):
        self._config = config or {}
        self._client = None   # lazy — do NOT import at module level

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import heavy_package  # type: ignore
            self._client = heavy_package.Client(...)
        except ImportError as exc:
            raise RuntimeError("pip install heavy_package required") from exc

    def do_thing(self, key: str) -> str:
        self._ensure_client()
        ...
```

### Step 3: Write the factory

Follow `PersistenceFactory` / `CacheFactory` exactly:

```python
# k9_factories/<concern>_factory.py
from threading import Lock
from typing import Any, Dict, Type
import logging

log = logging.getLogger("MyThingFactory")

class MyThingFactory:
    _registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs):
        raise RuntimeError("MyThingFactory is static")

    @staticmethod
    def _ensure_defaults() -> None:
        if MyThingFactory._bootstrapped:
            return
        with MyThingFactory._lock:
            if MyThingFactory._bootstrapped:
                return
            from k9_aif_abb.k9_<concern>.adapters.default_adapter import DefaultMyThingAdapter
            from k9_aif_abb.k9_<concern>.adapters.heavy_adapter   import HeavyMyThingAdapter
            MyThingFactory._registry.update({
                "default": DefaultMyThingAdapter,
                "heavy":   HeavyMyThingAdapter,
            })
            MyThingFactory._bootstrapped = True

    @staticmethod
    def register(name: str, cls: Type[Any]) -> None:
        MyThingFactory._ensure_defaults()
        with MyThingFactory._lock:
            MyThingFactory._registry[name.lower()] = cls

    @staticmethod
    def get(name: str, config: Dict[str, Any] = None):
        MyThingFactory._ensure_defaults()
        cls = MyThingFactory._registry.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown provider: {name}")
        return cls(config=config or {})

    @staticmethod
    def create(config: Dict[str, Any] = None):
        MyThingFactory._ensure_defaults()
        provider = (config or {}).get("<concern>", {}).get("provider", "default").lower()
        log.info("[Factory] Creating %s provider: %s", "<concern>", provider)
        return MyThingFactory.get(provider, config=config)
```

### Step 4: YAML config

```yaml
# No new required keys — default adapter works with zero config.
# To switch provider:
<concern>:
  provider: heavy      # default | heavy | custom
  # provider-specific keys here
  # credentials NEVER here — use environment variables
```

### Constraints (must hold for every adapter area)

- Credentials NEVER in `config.yaml` — use `os.environ.get("MY_KEY")` in the adapter
- Optional packages: lazy import in `_ensure_client()`, raise `RuntimeError` with install hint
- Factory `create(config)` always has a zero-config default — no config key required
- All new code is purely additive — no modification to existing classes
- Adapters accept `config=None` in `__init__` — factory always passes `config=cfg`

### Already-implemented adapter areas

| Concern | Contract | Default | Other adapters | Factory |
|---|---|---|---|---|
| Secret Management | `BaseSecretManager` | `EnvSecretAdapter` | Vault, AWS, IBM | `SecretManagerFactory` |
| Cache | `BaseCache` | `InMemoryAdapter` | `RedisAdapter` | `CacheFactory` |
| Object Storage | `BaseObjectStorage` | `LocalObjectStorageAdapter` | `S3ObjectStorageAdapter` (OOB — S3/MinIO), `IbmCosObjectStorageAdapter` | `ObjectStorageFactory` |

Usage in agent or service code:

```python
from k9_aif_abb.k9_factories.security_factory import SecretManagerFactory
from k9_aif_abb.k9_factories.cache_factory import CacheFactory
from k9_aif_abb.k9_factories.object_storage_factory import ObjectStorageFactory

sm    = SecretManagerFactory.create(self.config)   # default: env adapter
cache = CacheFactory.create(self.config)           # default: in_memory adapter
store = ObjectStorageFactory.create(self.config)   # default: local adapter

api_key = sm.get("MY_API_KEY")                     # raises KeyError if absent
cache.set("result:001", payload, ttl=300)

# Object storage — Router stores documents, agents retrieve by URI
uri  = store.upload("documents", "claim-001/form.pdf", file_bytes)
data = store.download("documents", "claim-001/form.pdf")
```

### Object storage — document flow

The Router is the single entry point and owns the object store. When a document event arrives:

```
UI upload → app_backend → Router
                            ├── 1. store_document(bucket, key, bytes) → URI
                            └── 2. publish JSON to domain topic
                                    { "document_uri": "s3://documents/claim-001/form.pdf",
                                      "filename": "form.pdf", "event_type": "document_received", ... }
                                          ↓
                                    Orchestrator → Squad → DocumentExtractorAgent
                                                            downloads from document_uri via ObjectStorageFactory
```

Config for S3 / MinIO:

```yaml
object_storage:
  provider: s3                                              # local | s3 | ibm
  endpoint_url: "${S3_ENDPOINT_URL:-http://localhost:9000}"  # MinIO
  region: "${S3_REGION:-us-east-1}"
# Credentials: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from env only
```

---

## Skill 12 — Apply the 4Ds AI Fluency Framework to Agent Design

The **4Ds** (Anthropic AI Fluency Framework) define four competencies for effective human-AI collaboration: **Delegation**, **Description**, **Discernment**, and **Diligence**. In K9-AIF, these map directly to agent YAML configuration and architectural decisions the Solutions Architect makes at design time.

Reference: `4Ds/AI Fluency_ Key Terminology Cheat Sheet.pdf`

### How the 4Ds map to K9-AIF

| 4D | K9-AIF equivalent | Where it lives |
|---|---|---|
| **Delegation** | Agent scope, HIL boundaries, interaction mode | Agent YAML `delegation:` section, SA design decision |
| **Description** | Agent prompt engineering — role, goal, instructions, output format | Agent YAML `role:`, `goal:`, `instructions:`, `output_schema:` |
| **Discernment** | Validation loops, governance checks, quality evaluation | `K9ValidationLoopAgent` config, governance pipeline |
| **Diligence** | Audit trail, transparency, deployment verification | Governance enforcement, `publish_event()`, record keeping |

### Delegation — deciding what the agent does vs what stays human

The SA must answer three questions per agent:

- **Problem Awareness** — what business problem does this agent solve? (captured in `description:`)
- **Platform Awareness** — what are the model's capabilities and limitations for this task? (captured in `model:` and model catalog capabilities)
- **Task Delegation** — what does the AI do, what does the human do? (captured in `delegation:`)

This also determines the **interaction mode**:

| Mode | K9-AIF pattern | When to use |
|---|---|---|
| **Automation** | `BaseAgent` (one-shot) | Deterministic tasks — triage, routing, classification, audit |
| **Augmentation** | `K9ValidationLoopAgent` + HIL escalation | Iterative tasks needing human review — fraud analysis, compliance |
| **Agency** | `K9PlanningLoopAgent` | Open-ended tasks where the agent plans its own steps — investigation, diagnosis |

### Description — the agent's prompt engineering contract

These are already first-class in the K9-AIF agent YAML:

| 4D sub-competency | Agent YAML field |
|---|---|
| **Product Description** — output format, audience, style | `output_schema:`, `instructions:` |
| **Process Description** — step-by-step reasoning approach | `instructions:`, `pattern:` (reasoning / extraction / chat / guardrails) |
| **Performance Description** — behavioral style (concise, detailed, challenging) | `role:`, `goal:` |

### Discernment — evaluating agent output quality

| 4D sub-competency | K9-AIF mechanism |
|---|---|
| **Product Discernment** — accuracy, coherence, relevance | `confidence_threshold` in validation loop config |
| **Process Discernment** — logical errors, reasoning quality | `should_continue()` evaluation in `K9ValidationLoopAgent` |
| **Performance Discernment** — communication effectiveness | Governance post-process pipeline, QA review |

### Diligence — responsible and ethical agent operation

| 4D sub-competency | K9-AIF mechanism |
|---|---|
| **Creation Diligence** — model selection rationale | Model catalog capabilities, `K9ModelRouter` scoring |
| **Transparency Diligence** — disclosing AI role | `publish_event()` audit trail, governance logging |
| **Deployment Diligence** — verifying outputs | `enforce_governance()`, HIL escalation via `ValidationDisposition.ESCALATE` |

### Agent YAML with 4D annotations

Add an optional `delegation:` section to the agent YAML to make the 4D design decisions explicit and self-documenting:

```yaml
name: FraudDetectionAgent
class: FraudDetectionAgent

description: >
  Correlates fraud signals across claims data using iterative validation.

pattern: reasoning
model: reasoning

role: >
  You are a fraud analyst evaluating insurance claims for indicators of fraud.

goal: >
  Identify fraud signals with high confidence, escalating ambiguous cases
  for human review rather than making false accusations.

instructions:
  - Cross-reference claim amount against policy limits
  - Check for temporal anomalies in claim submission
  - Flag geographic inconsistencies
  - Always include confidence score and evidence chain

output_schema:
  fraud_signals: list
  risk_score: float (0.0–1.0)
  confidence: float (0.0–1.0)
  evidence: list
  recommendation: string (approve | flag | escalate)

# 4Ds — AI Fluency design decisions
delegation:
  interaction_mode: augmentation
  ai_tasks:
    - signal correlation
    - pattern detection
    - evidence gathering
    - risk scoring
  human_tasks:
    - final fraud determination
    - investigation initiation
    - customer communication
  escalation_trigger: "confidence < 0.6 or risk_score > 0.8"

discernment:
  confidence_threshold: 0.8
  max_iterations: 5
  escalate_on_low_confidence: true

diligence:
  audit_trail: true
  requires_governance: true
  human_verification: required_above_threshold

governance:
  pre_process: true
  post_process: true
```

### SA checklist — applying the 4Ds to a new agent

Before writing any code, answer these for each agent:

1. **Delegation** — Is this automation (one-shot), augmentation (iterative + human), or agency (self-planning)? What tasks stay with the human?
2. **Description** — Is the role, goal, and output format precise enough that the LLM can produce consistent output? Are the instructions step-by-step?
3. **Discernment** — How do we know the output is good? What confidence threshold triggers escalation? Does this agent need a validation loop?
4. **Diligence** — Is governance enforced? Is the audit trail complete? Can a human verify the output before it is acted upon?

If the answer to any Discernment question is "we need to check and possibly retry," the agent should extend `K9ValidationLoopAgent`, not `BaseAgent`.

---

## Skill 13 — Add a new LLM provider adapter (Claude, Bedrock, OpenAI, etc.)

The framework ships with `OllamaLLM` as the OOB LLM adapter. To connect to a different provider (Anthropic Claude, AWS Bedrock, OpenAI, xAI Grok, IBM watsonx), implement a new adapter that extends `BaseLLM` and register it in `LLMFactory`.

**The framework is LLM-agnostic by design.** Agents, squads, orchestrators, and governance — none of them know or care which LLM provider is running underneath. They call `llm_invoke()`, and the factory + router + adapter chain handles the rest.

### Step 1: Implement the adapter

Extend `BaseLLM` (`k9_aif_abb/k9_core/inference/base_llm.py`). The contract is one method: `generate(prompt: str) -> str`.

```python
# k9_aif_abb/k9_core/inference/claude_llm.py

import os
from typing import Any, Optional
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class ClaudeLLM(BaseLLM):
    """LLM adapter for Anthropic Claude API."""

    layer = "Inference SBB — Claude"

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        timeout: int = 300,
        monitor: Optional[Any] = None,
        **kwargs: Any,
    ):
        super().__init__(name="ClaudeLLM", monitor=monitor)
        self.model = model
        self.timeout = timeout
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = os.environ.get(
            "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
        )
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        except ImportError:
            raise RuntimeError("pip install anthropic required")

    async def generate(self, prompt: str) -> str:
        self._ensure_client()
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text
            self.logger.info("[ClaudeLLM] %s responded (%d chars)", self.model, len(text))
            return text
        except Exception as e:
            self.logger.error("[ClaudeLLM] request failed: %s", e)
            return f"[WARN] Claude API failed: {e}"
```

**For AWS Bedrock**, the adapter would use `boto3` with the Bedrock runtime client instead of the Anthropic SDK directly. Same `BaseLLM` contract, different transport.

**For OpenAI / xAI / watsonx**, the pattern is identical — different SDK, same `generate()` contract.

### Step 2: Register in LLMFactory

`LLMFactory` uses a provider map to instantiate the right adapter. Add the new provider:

```python
# In LLMFactory.bootstrap() or via registration
from k9_aif_abb.k9_core.inference.claude_llm import ClaudeLLM

LLMFactory.register("claude", ClaudeLLM)
```

Or extend the bootstrap logic in `LLMFactory` to recognize the new backend.

### Step 3: Configure in config.yaml

```yaml
inference:
  llm_factory:
    backend: claude
    provider: anthropic
    base_url: "${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
    models:
      general:
        model: "claude-haiku-4-5-20251001"
        temperature: 0.3
        max_tokens: 4096
      reasoning:
        model: "claude-sonnet-4-20250514"
        temperature: 0.2
        max_tokens: 8192

  model_catalog:
    default_model: general
    models:
      general:
        provider: anthropic
        llm_ref: general
        capabilities: [general, chat, summarization]
        latency_tier: realtime
        cost_tier: standard
      reasoning:
        provider: anthropic
        llm_ref: reasoning
        capabilities: [reasoning, analysis, extraction]
        latency_tier: interactive
        cost_tier: premium
```

### Step 4: Credentials in .env only

```bash
# .env (never in config.yaml, never in git)
ANTHROPIC_API_KEY=sk-ant-...

# For AWS Bedrock:
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_DEFAULT_REGION=us-east-1
```

### What does NOT change

When switching providers, these remain **identical** — zero code changes:

- All agents (same `llm_invoke()` call)
- All squads (same YAML, same flow)
- All orchestrators (same `execute_flow()`)
- Router and Kafka topology
- Governance pipeline
- Validation loop behavior
- HITL gates
- Audit trail and event publishing
- UI and SSE streaming

The only changes are: (1) the adapter class, (2) `config.yaml` provider section, (3) `.env` credentials.

### Design constraints

- **Lazy imports** — adapter packages (`anthropic`, `boto3`, `openai`) are imported inside the adapter, not at module level. This avoids `ImportError` for teams that don't use that provider.
- **Credentials from env only** — never from `config.yaml`. Use `os.environ.get("KEY")`.
- **Timeout must be configurable** — production LLMs with large prompts can take minutes. Never hardcode.
- **Error handling** — return `[WARN]` prefixed string on failure (same convention as `OllamaLLM`). `llm_invoke()` detects this and raises `RuntimeError`.
- **Async generate** — `BaseLLM.generate()` can be sync or async. `K9ModelRouter.invoke()` handles both via `asyncio.run()` or direct call.

---

## Skill 14 — Chat session management (multi-turn conversation context)

LLM APIs (Claude, OpenAI, Ollama) are stateless — they don't store messages. Each API call is independent. To maintain a multi-turn conversation, the application must manage the message history and send the full context with every request.

K9-AIF provides the building blocks for this via `CacheFactory` (Redis/in-memory) and `SessionManager` (Postgres). The application decides which to use based on the use case.

### The problem

```
User: "What is the F-22's radar system?"
LLM:  "The F-22 uses the AN/APG-77 AESA radar..."

User: "What about its range?"           ← LLM has no idea what "its" refers to
LLM:  "Could you clarify what you mean?"  ← context lost
```

### The solution — config-driven session management

Enable chat sessions in `config.yaml`:

```yaml
chat:
  session_enabled: true
  provider: redis          # redis | memory | postgres
  ttl_seconds: 3600        # session expires after 1 hour of inactivity
  max_history: 50          # max messages per session (prevent unbounded growth)
```

### Step 1: Chat agent with session awareness

```python
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_factories.cache_factory import CacheFactory
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
import json


class ChatAgent(BaseAgent):

    layer = "Chat Agent SBB"

    def __init__(self, config=None, **kwargs):
        super().__init__(config or {}, **kwargs)
        self._session_enabled = self.config.get("chat", {}).get("session_enabled", False)
        self._max_history = self.config.get("chat", {}).get("max_history", 50)
        self._ttl = self.config.get("chat", {}).get("ttl_seconds", 3600)
        if self._session_enabled:
            self._cache = CacheFactory.create(self.config)
        else:
            self._cache = None

    def execute(self, payload: dict) -> dict:
        session_id = payload.get("session_id", "default")
        user_message = payload.get("message", "")

        # Build prompt with history
        if self._session_enabled and self._cache:
            history = self._get_history(session_id)
            history.append({"role": "user", "content": user_message})
            prompt = self._format_history(history)
        else:
            history = []
            prompt = user_message

        req = InferenceRequest(
            prompt=prompt,
            task_type="chat",
            metadata={"agent": self.layer, "session_id": session_id},
        )
        resp = llm_invoke(self.config, req)

        # Store updated history
        if self._session_enabled and self._cache:
            history.append({"role": "assistant", "content": resp.output})
            # Trim to max_history (keep most recent)
            if len(history) > self._max_history:
                history = history[-self._max_history:]
            self._cache.set(f"chat:{session_id}", json.dumps(history), ttl=self._ttl)

        return {
            "response": resp.output,
            "session_id": session_id,
            "model": resp.model_alias,
            "turn": len(history) // 2,
        }

    def _get_history(self, session_id: str) -> list:
        raw = self._cache.get(f"chat:{session_id}")
        if raw:
            return json.loads(raw)
        return []

    def _format_history(self, history: list) -> str:
        parts = []
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                parts.append(f"User: {content}")
            else:
                parts.append(f"Assistant: {content}")
        return "\n\n".join(parts)
```

### Step 2: API endpoint with session ID

```python
from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    session_id: str = None

@app.post("/chat")
def chat(payload: ChatRequest):
    session_id = payload.session_id or str(uuid.uuid4())
    result = agent.execute({
        "session_id": session_id,
        "message": payload.message,
    })
    return result
```

The UI sends `session_id` with every request. First request generates one; subsequent requests reuse it.

### Step 3: Config for each storage backend

**Redis (recommended for production):**

```yaml
cache:
  provider: redis

chat:
  session_enabled: true
  provider: redis
  ttl_seconds: 3600
  max_history: 50
```

```bash
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis
```

**In-memory (dev/testing only):**

```yaml
cache:
  provider: in_memory

chat:
  session_enabled: true
  provider: memory
  ttl_seconds: 3600
  max_history: 50
```

**PostgreSQL (audit trail, compliance):**

When chat history must be persisted for compliance or replay, use `SessionManager` on `BaseOrchestrator` with `session.enabled: true`. This stores turns in the `session_turns` table — queryable, auditable, no TTL expiry.

### What the framework provides vs what the application builds

| Concern | Framework ABB | Application SBB |
|---|---|---|
| Cache backend | `CacheFactory` → `RedisAdapter` / `InMemoryAdapter` | Config choice |
| Session persistence | `SessionManager` on `BaseOrchestrator` | Config choice |
| Message history format | — | Application decides (list of dicts, prompt template) |
| History truncation | — | Application decides (`max_history`) |
| Session ID generation | — | Application generates (UUID, user-based, etc.) |
| Prompt formatting | — | Application formats history into prompt string |

The framework provides the **storage and retrieval infrastructure**. The application decides **what to store and how to format it** for the LLM.

### Key considerations

- **Token limits** — long histories exceed LLM context windows. Use `max_history` to cap, or implement summarization (use the LLM to summarize older turns before including them).
- **TTL** — sessions should expire. A user who returns after 2 hours probably wants a fresh conversation. Redis TTL handles this automatically.
- **PII** — chat history may contain sensitive data. Use the `pii` flag on cache entries if the cache adapter supports it, and ensure TTL-based cleanup.
- **Multi-agent chat** — if a chat session involves multiple agents (e.g., intent classification → domain agent), the session ID is shared across all agents in the flow. The orchestrator passes it through.

### Reference: k9chat example

`examples/k9chat/` is the starting point for a chat application. Currently stateless — enhancing it with session management as described above makes it a complete multi-turn chat solution.

---

## Skill 15 — Streaming LLM responses (token-by-token output)

Batch inference (`llm_invoke`) waits for the complete response before returning — fine for document processing, wrong for chat. A user watching a 30-second wait with no feedback assumes something broke. Streaming sends text incrementally as the model produces it, the same way Claude's `converse_stream` or OpenAI's `stream=True` work.

K9-AIF supports this as an **additive, config-driven capability** — existing code is unaffected; streaming is opt-in per application.

### Architecture

```
BaseLLM.generate_stream()        ABB — optional, raises NotImplementedError by default
  └── OllamaLLM.generate_stream()    OOB SBB — Ollama NDJSON stream:true

BaseModelRouter.ainvoke_stream()  ABB — concrete default, falls back to ainvoke()
  └── K9ModelRouter.ainvoke_stream()  OOB — detects generate_stream(), streams real chunks

llm_invoke_stream(config, request)  utility — async generator, mirrors llm_invoke()
```

Every layer degrades gracefully: an LLM adapter without `generate_stream()` still works through `ainvoke_stream()`'s default (yields the complete response as one chunk). A custom `BaseModelRouter` that never overrides `ainvoke_stream()` still works the same way. **No existing code breaks** — this is why the new methods are concrete with sane defaults, not abstract.

### Step 1: Enable streaming in agent config

```yaml
# config.yaml
chat:
  stream: true   # config-driven — false (or omit) for non-streaming
```

### Step 2: Add a streaming execute method to the agent

Keep `execute()` as-is for any caller that wants the synchronous, complete-response contract. Add `execute_stream()` alongside it — don't replace.

```python
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke_stream

class ChatAgent(BaseAgent):

    def execute(self, payload: dict) -> dict:
        # unchanged — full response, synchronous
        ...

    async def execute_stream(self, payload: dict):
        """Yield response chunks incrementally. Used when chat.stream: true."""
        prompt = payload.get("text", "")
        req = InferenceRequest(prompt=prompt, task_type="chat")

        async for chunk in llm_invoke_stream(self.config, req):
            yield chunk
```

### Step 3: Wire an SSE endpoint in the application

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    async def event_generator():
        async for chunk in agent.execute_stream({"text": payload.message}):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Step 4: Consume the stream in the browser

```javascript
const response = await fetch("/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: text }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "", fullText = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n\n");
  buffer = lines.pop();
  for (const line of lines) {
    if (!line.startsWith("data: ")) continue;
    const data = JSON.parse(line.slice(6));
    if (data.chunk) { fullText += data.chunk; bubble.textContent = fullText; }
    if (data.done) return;
  }
}
```

### Toggling streaming OFF

Set `chat.stream: false` (or omit the key). The agent and app code don't need an `if streaming` branch — `is_streaming_enabled()` (or equivalent config read) tells the frontend which endpoint to call (`/chat` vs `/chat/stream`), and the backend `execute()` path is unchanged.

### Reference implementation

`examples/k9chat/` — `chat_agent.py` (`execute_stream()`), `chat.py` (`send_message_stream()`, `is_streaming_enabled()`), `app.py` (`/chat/stream` SSE endpoint, `/chat/config`), `templates/index.html` (fetch + ReadableStream consumer). Toggle via `chat.stream` in `config.yaml`.

### Building a streaming adapter for a new LLM provider

When adding a provider (see Skill 13), implement `generate_stream()` alongside `generate()`:

```python
class ClaudeLLM(BaseLLM):
    async def generate(self, prompt, system_prompt=None) -> str:
        ...  # existing non-streaming implementation

    async def generate_stream(self, prompt, system_prompt=None):
        # Claude's streaming API yields events; extract text deltas
        with self._client.messages.stream(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
```

`K9ModelRouter.ainvoke_stream()` detects `generate_stream()` automatically via `hasattr()` — no router changes needed when adding a new provider.

---

## Skill 16 — Add an external framework or vendor adapter

This is a different shape from Skill 11 (internal infra concerns: cache, secret management) and Skill 13 (LLM providers, which plug into the inference chain specifically). This skill is for wrapping something K9-AIF doesn't own at all — a whole external agent framework, or a third-party enterprise tool (identity provider, SIEM, ITSM) — so it operates inside K9-AIF's governance boundary instead of beside it.

**Two shipped precedents exist. Read the code, not just this skill, before building a third.**

- `k9_aif_abb/k9_adapters/crewai/` — wraps an unmodified CrewAI `Crew` at the **Orchestrator** layer, because a `Crew` is itself a multi-agent orchestrating construct with its own `kickoff()`.
- `k9_aif_abb/k9_adapters/claude_agent_sdk/` — wraps the Claude Agent SDK's own autonomous tool-use loop at the **Agent** layer, because its natural unit of encapsulation is one session, not a crew. Also documents the harder, more honest case: this substrate can be action-governed (every tool call routed through `apply_post_governance()`) but not inference-governed (no model-injection seam exists in the SDK — verified from its source, not assumed). See that package's own `CLAUDE.md` for the full conformance-tier reasoning.

### Step 1: Find the framework's natural unit of encapsulation

Ask what the external thing's own internal delegation/session concept is — a crew of agents, a single autonomous session, a single tool call — before deciding which K9-AIF layer it should extend alongside `BaseAdapter`. Wrapping at the wrong layer (e.g., treating a single-session SDK as if it were a crew) forces an awkward contract on both sides. This is the same rule of thumb documented independently in the Pet Store Agentic reference implementation (`k9-aif-examples/Work-In-Progress/K9-AIF-and-Claude-Agent-SDK/Architecture_Guide.md`, Principle 1) — two unrelated projects converging on the same answer is a good sign the rule is real, not local preference.

### Step 2: Build the three-piece shape

Both precedents use the same three classes:

```
K9<Framework>Adapter            ← facade: accept a K9-AIF payload, return a K9-AIF result
<Framework>OrchestratorAdapter  ← extends BaseAdapter + BaseOrchestrator (or BaseAgent,
                                   per Step 1); owns the actual wrapped session/crew/loop
<Framework>PayloadMapper        ← to_<framework>_input() / from_<framework>_output(),
                                   called exactly once, at the facade layer only
```

The facade never accepts a pre-built framework-native options object — it constructs one itself from its own capability registry, every call. Accepting a caller-supplied one (the way `CrewAIOrchestratorAdapter` accepts a pre-built `crew`, deliberately, since a `Crew`'s internal task graph isn't a security boundary the way an SDK's tool grants are) means trusting whatever was already wired into it — which defeats the reason to wrap the framework at all when the wrapped thing's own delegation or tool-grant mechanism *is* the boundary you're trying to close. Match the stricter precedent (`claude_agent_sdk`), not the looser one, unless you have the same reason `crewai` had for the looser choice.

Route every governed action through the adapter's inherited `apply_pre_governance()` / `apply_post_governance()` — never a bespoke check local to the new adapter. If the wrapped framework has its own fan-out/delegation concept (subagents, internal task chaining), disable it at the wrapping boundary or prove every path through it is independently routed through the same governance calls — an untracked second delegation path is not a smaller version of the problem, it's the whole problem, because K9-AIF's provenance graph will silently under-report rather than error.

### Step 3: Vendor/security-tool adapters — a target shape, not shipped code

The Zero Trust Execution Layer's `VERIFY → EVALUATE → DECIDE → ENFORCE → OBSERVE` pipeline is designed to accept exactly this kind of external adapter at each stage — an identity provider feeding `VERIFY`, a policy engine feeding `EVALUATE`, a SIEM or ITSM tool consuming `OBSERVE`'s audit stream. **As of this writing, none of these are built.** No Zscaler, Okta, ServiceNow, or Microsoft Defender/Purview/Sentinel adapter exists anywhere in this repository — grep `k9_aif_abb/` before assuming otherwise. What exists is the pattern this skill documents, proven twice for external *agent* frameworks, and a target-architecture diagram (`docs/diagrams/k9-aif-consumers-producers.png`) showing where such adapters would sit if an organization builds them.

If you are the organization building one: it is a fourth instance of the same three-piece shape above, wrapping whichever stage of the Zero Trust pipeline the vendor tool feeds — not a new pattern. Do not present a vendor name in documentation or diagrams as an implemented capability until an adapter under `k9_aif_abb/k9_adapters/<vendor>/` actually exists and is tested; a target diagram is a floor plan, not a certificate of occupancy.
