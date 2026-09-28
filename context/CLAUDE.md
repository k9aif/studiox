# CLAUDE.md

Guidance for Claude Code in this repository. Step-by-step recipes live in
`SKILLS.md` — **read it
directly when doing one of those tasks; it is no longer auto-imported here**,
so don't assume its contents are already in context.

## What this is

K9-AIF: architecture-first framework for governed, observable, multi-agent
systems, built on OOA/OOD/TOGAF discipline. ABB (Architecture Building Block)
= abstract contract in `k9_core/`. SBB (Solution Building Block) = concrete
implementation extending an ABB, in `examples/<App>/` or `k9_projects/<App>/`.
Liskov Substitution and Open/Closed are non-negotiable — new capability
extends a `Base<Concern>` contract, never edits one.

Diagrams default to PlantUML. BPMN swim lanes: horizontal bands top-to-bottom,
labels left, activities left-to-right within a lane.

`BaseComponent` does **not** extend `ABC`. An ABB needing both infra
(logging/monitoring/message bus) and enforced abstract methods extends
`(BaseComponent, ABC)` — correct multiple inheritance, not redundant. Never
assume a parent already extends `ABC` without checking.

## Execution hierarchy

```
Event → K9EventRouter → known event_type → domain topic
                       → unknown → intent.in → IntentOrchestrator → domain topic
domain topic → Orchestrator → 1+ Squads → 1+ Agents → LLM
```

**Three-layer decoupling — never violate:** each layer knows only the layer
directly below it. Router imports/references Orchestrators only, never
Squads or Agents. Orchestrator imports Squads only, never Agents. Squad YAML
has no `orchestrator:` field; Agent YAML has no `squad:`/`routing:` fields.
Agent registration happens in the app entry point, not inside the
orchestrator.

Cardinality: Router 1→N Orchestrators, Orchestrator 1→N Squads
(`execute_squads(..., parallel=True/False)`), Squad 1→N Agents (sequential
`flow`).

## LLM calls — one path only

Agents never call `OllamaLLM`/`LLMFactory` **or `ModelRouterFactory`/
`router.invoke()`** directly — only `llm_invoke.py` itself is allowed to
touch the router. Always:

```python
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
resp = llm_invoke(self.config, InferenceRequest(prompt=..., task_type=...))
```

`llm_invoke` raises `RuntimeError` on failure — it never silently returns
empty output; catch and handle explicitly. It also retries on an empty
response (a hybrid-reasoning model burning its whole token budget on
invisible "thinking" and returning 0 chars is a real, observed failure
mode) and emits the `LLMCall` trace event — both silently lost if an agent
calls `router.invoke()` directly instead. Found live in k9chat's
`ChatAgent.execute()` plus four other agents across two example apps
(2026-09-21) — `check-llm-invoke.sh` (see Hooks below) now catches this
automatically on every write/edit. Full chain + adding a new provider:
`SKILLS.md` Skills 2 and 13.

**BaseAgent vs K9ValidationLoopAgent vs K9PlanningLoopAgent** — the
generator/scaffold defaults every agent to one-shot `BaseAgent`. Ask per
agent: one-pass answer → `BaseAgent`; iterative convergence on a confidence
score → `K9ValidationLoopAgent`; agent must plan and revise its own steps →
`K9PlanningLoopAgent`. Full recipe: `SKILLS.md` Skill 10.

## Governance

Every agent gets a governance pipeline via `require_governance()` at init.
`K9_ENV=development|test` → `NoopGovernance` permitted (WARNING logged).
`K9_ENV=production|staging` → `enforce_governance()` **raises**
`PermissionError` if governance isn't configured. An agent that never calls
`self.enforce_governance()` in `execute()` silently runs `NoopGovernance`
even in production — the most common real bug in new agent code.

**`enforce_governance()` does not run any checks.** It only asserts that
governance isn't `NoopGovernance` — a "did anyone configure real governance
at all" guard. The methods that actually run checks are
`apply_pre_governance(payload)` / `apply_post_governance(result)`
(`BaseAgent`, and identically on `BaseOrchestrator`/`BaseRouter` — separate,
duplicated methods, not inherited from one place), which call
`self.governance.pre_process`/`post_process`. **Only the loop agents call
them for you** (`BaseValidationLoopAgent`, `BaseCriticActorAgent` and their
subclasses — see the Shield section below). `BaseAgent`, `BaseOrchestrator`
and `BaseRouter` never do: a custom agent, every orchestrator and every
router must call them itself, same as `enforce_governance()`. Calling only
`enforce_governance()` gives zero content-level protection even though it
looks like "governance is on."

**The hooks are `async`; `BaseAgent.execute()` and `execute_flow()` are
sync.** Calling `self.apply_pre_governance(payload)` without awaiting it
returns an un-run coroutine — no check runs, no error is raised. From sync
code use `_run_coro_sync(self.apply_pre_governance(payload))` (the bridge
the loop agents and `BaseOrchestrator` use; safe inside a running event
loop, unlike `asyncio.run()`/`run_until_complete()`). Orchestrators also
have a sync ingress wrapper, `apply_shield(payload)` →
`{"allowed", "reason", "payload"}`.

`require_governance()` never fails at init: with no governance passed it
returns `NoopGovernance` in every environment (WARNING in
development/test, ERROR otherwise; `K9_ENV` unset means `production`). The
hard fail happens only where `enforce_governance()` is called.

## Security / Vulnerability (k9x_Shield) and Zero Trust

Two independent, non-overlapping security layers ship in the framework —
know which one a question is actually about before answering it:

**k9x_Shield** (`k9_security/vulnerability/`) — 13 concrete
`BaseVulnerabilityCheck` subclasses (`checks/`: `InputSizeCheck`,
`PromptInjectionCheck`, `PIIBoundaryCheck`, `PIIRequestCheck`,
`SemanticDriftCheck`, `ToolArgumentCheck`, `ToolAuthorizationCheck`,
`ExecutionGuardCheck`, `HardcodedCredentialCheck`, `MemoryPoisoningCheck`,
`SystemPromptLeakageCheck`, `OutputSanitizationCheck`,
`RequestFrequencyCheck`), run in order by `VulnerabilityChain`
(`vulnerability_chain.py`), wrapped by `ShieldGovernance`
(`shield_governance.py`) — a concrete `pre_process`/`post_process`
implementation, i.e. a drop-in `governance=` value for any `BaseAgent`/
`BaseOrchestrator`/`BaseRouter`. A `BLOCK`-status check (or a `FLAG` when
`strict=True`) makes `ShieldGovernance` **raise `PermissionError`** — that
raise is the only block signal; there is no return-value sentinel. A `FLAG`
under `strict=False` (the common config) just logs and lets the payload
through unmodified — `ShieldGovernance` never mutates a passing payload.
`fail_open` (default `True`) controls what happens if a check itself
raises: `True` → treated as FLAG, `False` → treated as BLOCK.

**Shield is off in the shipped configuration.** `k9_aif_abb/config/config.yaml`
sets `security.shield.enabled: false` ("SBBs enable and configure in their
own config.yaml"), while `ShieldGovernance`'s code fallback when the key is
absent is `enabled=True`. So a solution that copies the framework config
gets no Shield checks until it sets `security.shield.enabled: true` **and**
passes `governance=ShieldGovernance(...)` to each component. Don't tell
anyone Shield is on by default without checking which config is loaded.

**`ShieldGovernance(config)` runs only the checks listed** under
`security.shield.ingress.checks` / `egress.checks`, and takes the *whole*
config (it reads `config["security"]["shield"]`). With `enabled: true` and
no check lists — or passed the shield block itself instead of the whole
config — it builds empty chains, still logs `enabled=True`, and blocks
nothing (verified: a prompt-injection payload passes). Copy the check lists
from the framework's `config.yaml`, and prove it with one injection test.

**The checks are correct and well-tested** (`tests/test_shield_governance.py`).
**Where the hooks are called for you (since 6b55f6b, shipped in 1.12.x):**
`BaseValidationLoopAgent.execute()` and `BaseCriticActorAgent.execute()` —
the two most commonly generated agent patterns, plus anything extending them
(e.g. `K9PlanningLoopAgent`) — wrap `_execute_loop()` with real
`apply_pre_governance`/`apply_post_governance` calls. Put loop logic in
`_execute_loop()`; **overriding `execute()` itself bypasses governance.**

**Where they are not:** a custom agent extending `BaseAgent` directly gets
**zero enforcement** from `governance=ShieldGovernance(...)` unless its own
`execute()` explicitly calls the hooks. Don't assume "this agent has
`ShieldGovernance` wired" means anything is actually being checked — verify
the hooks are called, not just that the object was constructed.

**Zero Trust** (`k9_security/zero_trust/`) — a separate mechanism,
identity/risk/authorization-based rather than pattern-matching-based:
`ExecutionContext` → `BaseZeroTrustGuard.evaluate()` (default
`DefaultZeroTrustGuard`: compromise check → role-based authorization →
data-loss/masking → risk scoring) → `TrustDecision`. Lives on
`BaseOrchestrator` only (`apply_zero_trust()`, not on `BaseAgent`/
`BaseRouter`), gated by `enable_zero_trust` (config key, **defaults
`False`** — `apply_zero_trust()` returns an unconditional
`{"allowed": True, "decision": "BYPASSED", ...}` bypass when off, so
calling it costs nothing when disabled but also protects nothing).
`DefaultZeroTrustGuard`'s built-in `PromptInjectionGuard` is a **plain
substring match** against 6 fixed phrases (`k9_security/zero_trust/guards.py`)
— materially weaker than Shield's regex-based `PromptInjectionCheck`
(handles `ignore (all|any) previous instructions`, `PromptInjectionGuard`
only matches the literal phrase `"ignore previous instructions"` — inserting
one word defeats it). Treat Zero Trust and Shield as additive, not
redundant: Zero Trust's real value is its authorization/risk-scoring/
data-masking machinery (`RoleBasedAuthorizationGuard`,
`SensitiveDataLossGuard`), not its compromise check.

**k9x_satan** (`k9x-ecosystem/k9x_satan`) is the reference implementation
proving these layers actually contain a real attack end-to-end — read its
own `CLAUDE.md` for the full Router-ingress/Orchestrator-egress containment
contract before assuming a generated app gets that containment "for free."
It doesn't, without explicit wiring — satan builds its own.

## MCP tools

Three built-in client transports, all behind `MCPClientConnectionFactory.get(name, config={...})`
(built-ins are registered by import path and imported only when requested):

| Name | Class | Use for |
|---|---|---|
| `streamable_http` | `MCPStreamableHttpConnector` | **Any hosted, standard MCP server** (e.g. FastMCP at `http://host:port/mcp`). Official SDK, real handshake. Needs `pip install "k9-aif[mcp]"`; works on SDK 1.x and 2.x |
| `http` | `MCPHttpConnector` | Only servers exposing the REST convention `GET /tools`, `POST /tools/call`. **404s on a standard MCP server** — not MCP over HTTP despite the name |
| `stdio` | `MCPStdioConnector` | Spawning a local MCP server process |

`MCPStreamableHttpConnector` opens one MCP session per call (`connect()`/
`close()` hold nothing) because the SDK's anyio cancel scopes are bound to
the task that opened them. `call_tool()` returns the tool's structured
result as a dict (FastMCP's `{"result": ...}` wrapper removed) and raises
`MCPToolError` when the server reports the call failed. Added in 1.12.4
(G-24); 1.12.3 had it but breaks on SDK 2.x — never pin 1.12.3.

`BaseMCPAgent` is the abstract base for tool-calling agents (`connect`/
`send_request`/`close`); `MCPClientAgent` is a **stub** whose methods raise
`NotImplementedError` — don't build on it. Serving tools:
`k9_mcp/servers/BaseMCPServer` (`handle_request`) is the ABB for a tool you
implement yourself; it defines no network transport of its own.

## Model routers

Every call goes through `llm_invoke` → `ModelRouterFactory.get_router(config)`
→ a `BaseModelRouter`. `inference.router.type` selects only the built-ins
(`k9` / `k9_model_router`, or `default`; anything else raises
`ValueError: Unsupported router type`); there is **no public
registry for a custom router type yet** (a router registry mirroring the
provider registry is proposed). Today a solution plugs in its own router by
building it at start-up and placing it in `ModelRouterFactory._instances`
under the factory's cache key — exactly what the EOC does with
`EOCModelRouter` (`examples/K9X_Enterprise_Insurance_OperationsCenter/api/app.py`).
Agents are unaffected either way.

## Everything is provisioned through factories

Never instantiate directly in application code: `LLMFactory`,
`ModelRouterFactory`, `AgentRegistry`, `OrchestratorRegistry`,
`SecretManagerFactory`, `CacheFactory`, `ObjectStorageFactory`. Every factory
`create(config)` has a zero-config default (env secrets, in-memory cache,
local storage) — no config key required for the common case. Adding a new
provider to any of these: `SKILLS.md` Skill 11.

## Kafka ownership

Only the **Router** (domain topics) and **Orchestrator** (results /
downstream topics) touch Kafka directly — this hasn't changed. Agents are
constructed without a `message_bus` — they share data sequentially through
the Squad flow, not via A2A messaging. `publish_event()` on an agent reaches
the logger/monitor only.

**One narrow, deliberate exception: triggering HIL.** An Agent or Squad may
raise `RequiresHIL` to signal that a human decision is needed mid-flow (a
fraud score below threshold, an `ESCALATE` disposition, a Squad synthesizing
across agents) — this is a controlled propagation, not a Kafka publish. The
signal is *raised* at Agent/Squad depth and *caught* at the Orchestrator,
which remains the only layer that actually calls `message_bus.publish_to()`
and the only layer that decides execution halts. Never let an Agent or
Squad call `message_bus` directly, even for HIL — this isn't layering
purity, it's a consistency requirement: a Kafka publish issued below the
layer that controls whether execution continues can't stop the rest of the
flow from completing normally, which produces exactly the outcome
`RequiresHIL` exists to prevent — a workflow reporting itself "completed"
while a human is still being asked to review it. See the HIL section below
for the full mechanism (signal shape, Orchestrator-side halt + state
persistence, Router-side resume).

## HIL (Human-in-the-Loop)

`RequiresHIL` (`k9_core/orchestration/hil_signal.py`) is raised by an Agent
or Squad to trigger a human decision mid-flow. It propagates by exception
through the normal Agent → Squad → Orchestrator call chain (confirmed:
`BaseSquad.execute()` logs and re-raises, never swallows) — never a
return-value flag, so it can't be silently dropped by a Squad author who
never thought about HIL.

**Catch it in your SBB orchestrator's `execute_flow()`:**

```python
from k9_aif_abb.k9_core.orchestration.hil_signal import RequiresHIL

def execute_flow(self, payload):
    try:
        results = self.execute_squads([self.fraud_squad], payload)
    except RequiresHIL as exc:
        return self.handle_requires_hil(exc, payload)
    return {"status": "completed", **results}
```

`handle_requires_hil()` delegates to a composed `BaseHILOrchestrator` —
publishes `hil.requests.<queue>` (queue defaults to a slugified form of
the catching orchestrator's `layer`), persists a `hil_pending` row via
`RoutingStateStore` (correlation_id, which orchestrator/module to resume,
the payload to resume it with — not just a topic name), and returns
`{"status": "pending_hil", "correlation_id": ..., ...}` immediately.
**Never blocks** — a HIL review can take hours or days.

`K9EventRouter.listen_for_hil_replies()` subscribes once, across every
`hil.replies.*` topic (`K9EventBus.subscribe_async(..., pattern=...)`) —
job-id belongs in the message (`correlation_id`), never in the topic name;
one Router, not one consumer per orchestrator type. On a reply,
`_on_hil_reply()` first resolves the pending row by `correlation_id` with an
atomic compare-and-swap (`resolve_hil_pending()`: `pending` → `resolved`,
returns whether it won — since 1.12.1, G-16), and only if it won merges the
decision into the resumed payload as `hil_decision` and calls `route()` on
it. A duplicate reply (Kafka redelivery, outbox retry, a second Router)
therefore resumes the flow exactly once. Resuming is just re-routing with
new information now available, reusing the same method that handles any
other event, not a second mechanism.

**Open (G-18):** the row is marked resolved *before* re-routing, so a crash
between the two loses that resume. A `resuming` state plus recovery sweep
is planned; until then the SBB orchestrator's resume branch must be
idempotent.

**Request fields not yet passed:** `BaseHILOrchestrator.execute_flow()`
builds the request from `title`/`reason`/`priority`/`source_orchestrator`
plus `payload` (the `RequiresHIL` context). It does not pass per-task TTL,
PII field lists, required role, or `artifacts` — the list of object-storage
links (`s3://bucket/key`, S3/MinIO) that k9x-hil reads to fetch the review
document directly. k9x-hil falls back to queue defaults for the first
three; a solution that needs documents shown to the reviewer must add
`artifacts` itself.

**Not every HIL-consumer action is a decision worth publishing.** The
reference reply-side implementation, `k9x-hil`
(`backend/task_actions.py`), only publishes to `reply_to` on a *terminal*
decision — `complete` / `reject` / `expire`. `claim` and `start` aren't
decisions (someone picked the task up, nothing for a waiting flow to
resume on yet), and `escalate` isn't terminal either — the task stays
in-flight for someone else to act on; whichever terminal action
eventually lands on it is what publishes, not the escalation itself. Any
other HIL consumer you build should draw the same line — publish on
outcomes, not on intermediate state changes — or a waiting flow resumes
prematurely on a decision that hasn't actually been made yet.

**Two deliberate rule carve-outs, both documented, neither accidental:**
1. The Kafka-ownership rule above — Agent/Squad may *raise* `RequiresHIL`,
   but only the Orchestrator that catches it ever calls
   `message_bus.publish_to()`.
2. `BaseOrchestrator.handle_requires_hil()` calls a real, separate
   `BaseHILOrchestrator` instance — a genuine Orchestrator-to-Orchestrator
   call, otherwise disallowed. Chosen deliberately (composing it as a
   plain collaborator method was the alternative) so Studio's own "HIL
   Orchestrator" canvas component maps onto something that's actually
   invocable, not just a UI label.

`hil_pending`'s `payload` column persists the *resume* payload (original
`event_type` included) — the Router's own registered `routing.table`
resolves where it goes next, exactly as it would for any fresh event; no
separate resume-topic lookup exists or is needed. Full sequence:
`docs/diagrams/hil_roundtrip_sequence.puml` /
`README.md`'s Human-in-the-Loop section.

**Known limitation, not yet solved:** `BaseHILOrchestrator`'s and
`K9EventRouter`'s zero-config state-store bootstraps must resolve to the
*same* backing DB (same `db_path`, or an explicitly shared `state_store=`)
or a reply can never find the row it's meant to resolve — nothing enforces
this automatically today; get it wrong and replies are silently dropped
(logged as "matches no pending flow", not raised).

## Pre-Push Checklist

- Every new `.py` file starts with the two-line header
  `# SPDX-License-Identifier: Apache-2.0` / `# K9-AIF Framework`, before any
  module docstring. Nearly universal in `k9_aif_abb/` but not enforced by
  any hook — check new files by hand; a whole adapter package (CrewAI) went
  missing it for a full release cycle before anyone noticed.
- No hardcoded IPs (`192.168.x.x` etc.) — env vars with localhost defaults:
  `"${POSTGRES_HOST:-localhost}"`, `"${OLLAMA_BASE_URL:-http://localhost:11434}"`
- No credentials in `config.yaml` — secrets in `.env` (gitignored) only
- `.env` never staged; example apps and generated projects ship an
  `env-example` template — copy it, never commit the real `.env`
- No `__pycache__`/`.pyc` — `.gitignore` present before first commit
- Three-layer decoupling preserved (see above)
- After any `k9_aif_abb/` change: `./generate_pdoc.sh` (the `./` matters —
  without it, pdoc silently documents whatever `k9-aif` is pip-installed in
  `.venv` instead of the local tree) and commit `docs/pydocs/` in the same
  commit

## Hooks (`.claude/settings.json`, run automatically, exit 2 = blocked)

| Hook | Triggers on | Checks |
|---|---|---|
| `check-python.sh` | any `*.py` write/edit | Python syntax |
| `check-yaml.sh` | any `*.yaml`/`*.yml` write/edit | YAML validity |
| `run-abb-tests.sh` | files under `k9_aif_abb/` | `test_framework.py` + `test_intelligent_model_router.py` |
| `check-governance.sh` | `*.py` under `examples/` | warns if `NoopGovernance` appears |
| `check-init-docstring.sh` | any `__init__.py` | warns if module docstring missing |
| `check-llm-invoke.sh` | `*.py` under `examples/` or `k9_projects/` | warns if `router.invoke()`/`ModelRouterFactory.get_router()` appears outside `llm_invoke.py` |

## Commands

```bash
# Setup
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Tests
pytest k9_aif_abb/tests/ -v                      # all
pytest k9_aif_abb/tests/test_framework.py -v     # framework stability only, no external services

# Run example apps (local)
# k9chat moved to github.com/k9aif/examples (k9-aif-examples) 2026-09-21 --
# see that repo's k9chat/README.md for its own run instructions.
./run_acme_support_center.sh

# EOC (RHEL/Podman) — after git pull, always rebuild; restart alone won't pick up code
bash build.sh && bash run_eoc_pod.sh
sudo podman pod ps
sudo podman logs eoc-app-backend

# Generate a stub app -- via K9X Studio (k9x-ecosystem/k9x_studio), not a CLI script
```

## Known gotchas (not obvious from the code alone)

- `K9ModelRouter.invoke()` bridges sync `BaseAgent.execute()` to async
  `BaseLLM.generate()` via `_run_coro_sync()` — never call `asyncio.run()`
  directly there. Inside an already-running event loop (FastAPI etc.),
  `asyncio.run()` raises, and a broad `except Exception` upstream will
  silently swallow it and fall back to stub output.
- Any new `BaseLLM.generate()` implementation must accept
  `system_prompt=None` — `K9ModelRouter` always passes it as a kwarg.
- `persistence.enabled: false` / `provider: memory` must still resolve to a
  SQLAlchemy-capable store — `RoutingStateStore` needs `.metadata`/`.engine`,
  which plain `MemoryPersistence` doesn't provide. Resolves to
  `SQLiteDatabaseStorage(db_path=":memory:")` instead.

## Reference

**Unknown intents.** When the Router can't map an `event_type`, it
publishes to `intent.in`; `IntentOrchestrator` (`k9_orchestrators/`) runs
`IntentSquad` (`k9_squad/`) with a `BaseIntentAgent` (OOB `K9IntentAgent`:
`intent_map` lookup → LLM via `llm_invoke` → `fallback_intent()`) and
re-publishes to the domain topic, or returns a "please clarify" response.
Nothing is ever wired *in front of* the Router. Below `confidence_threshold`
(default 0.5) `IntentSquad.on_low_confidence()` fires.

**Config.** Two levels: the framework's `k9_aif_abb/config/config.yaml`
(test defaults: Ollama, SQLite, Shield off) and each solution's own
`config/config.yaml`, which overrides it. Key sections:
`inference.llm_factory.models`, `inference.model_catalog`,
`inference.router.persistence` (sqlite | postgres | memory), `postgres`,
`messaging`, `security.shield`.

**Persistence.** `RoutingStateStore` (`k9_storage/routing_state_store.py`)
holds `sessions`, `session_turns`, `routing_decisions`, `context_artifacts`
and `hil_pending` — SQLite auto-created, PostgreSQL by reflection;
`postgres.schema` must match the real schema or reflection misses tables.

**Sessions.** `BaseOrchestrator` wires a session manager only when
`session.enabled: true` (`_bootstrap_session`); no key, no overhead.

**Infrastructure (env vars, localhost defaults — never hardcode IPs):**
`OLLAMA_BASE_URL` (:11434), `POSTGRES_HOST` (:5432), `KAFKA_BROKER` (:9092),
`NEO4J_URI` (bolt :7687), `DOCLING_ENDPOINT` (:5001), `S3_ENDPOINT_URL`
(:9000, with `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`), `MCP_SERVER_URL`
for a hosted MCP server, `K9_ENV` for governance enforcement.

**Canonical example:** `examples/K9X_Enterprise_Insurance_OperationsCenter/`
— three processes (FastAPI app + UI, Kafka router, orchestrator consumer),
per-domain orchestrators, zero trust, custom model router.

Step-by-step recipes (new agent, new provider, new factory backend, Squad/
Agent YAML, validation loops, HIL wiring): `SKILLS.md`. Anything else:
the source under `k9_aif_abb/` is authoritative over any doc, this one
included.
