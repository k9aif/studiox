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
  → OllamaLLM.invoke(prompt)                  # hits Ollama at 192.168.1.98:11434
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
`K9ModelRouter` is the **OOB default SBB** — a ready-to-use extension that scores models from the catalog using weighted signals. It is not mandatory.

If a solution needs different routing logic (cost optimization, compliance routing, A/B testing, provider switching), extend `BaseModelRouter` and register it via config. The rest of the framework — agents, squads, orchestrators — is unaffected.

### Step 1: Extend `BaseModelRouter`

```python
# examples/<App>/routers/my_router.py

from k9_aif_abb.k9_inference.routers.base_model_router import BaseModelRouter
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_inference.models.route_decision import RouteDecision


class MyRouter(BaseModelRouter):

    def route(self, request: InferenceRequest) -> RouteDecision:
        # Your routing logic here — pick a model alias from the catalog
        alias = "reasoning" if request.task_type == "reasoning" else "general"
        return RouteDecision(model_alias=alias)

    def invoke(self, request: InferenceRequest):
        decision = self.route(request)
        llm = self._get_llm(decision.model_alias)   # inherited helper
        return llm.invoke(request.prompt)
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
        └── K9ValidationLoopAgent   (LLM-driven OOB)
              └── FraudValidationAgent   (domain SBB — overrides only what differs)
```

### Solutions Architect decision — BaseAgent vs K9ValidationLoopAgent

> **The generator, intake, and Claude Code scaffold all agents extending `BaseAgent` by default.** This is correct for most agents. The SA must explicitly decide at design time which agents need the validation loop.

Ask this question for every agent during design:

> *"Does this agent need to test something, observe the result, and decide whether to try again — or does it produce its answer in one pass?"*

| Answer | Extend |
|---|---|
| One-pass — classify, route, audit, guard, sync | `BaseAgent` |
| Iterative convergence — fraud, evidence, compliance, document confidence | `K9ValidationLoopAgent` |

When changing a generated agent from one-shot to iterative, replace the parent class and swap `execute()` for the five loop methods:

| Remove | Add |
|---|---|
| `class MyAgent(BaseAgent)` | `class MyAgent(K9ValidationLoopAgent)` |
| `def execute(self, payload)` | `def generate_hypothesis(self, loop_ctx)` |
| | `def run_validation(self, hypothesis, loop_ctx)` |
| | `def evaluate_observation(self, tool_result, loop_ctx)` |
| | `def should_continue(self, observation, loop_ctx)` |
| | `def finalize(self, loop_ctx) -> ValidationLoopResult` |

**EOC reference agents requiring this migration:**
- `FraudDetectionAgent` — fraud signal correlation across multiple passes is the canonical iterative use case
- `DocumentExtractorAgent` — extraction confidence check + re-extraction on parse failure benefits from iterative refinement
