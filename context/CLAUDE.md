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

**K9-AIF alone is enough to build a complete application.** No other agent
framework is needed: Router → Orchestrator → Squad → Agent, governance,
inference, persistence, messaging and HIL are all here (DAS, K9X SATAN,
Sentinel and HIL depend on nothing else). Never add CrewAI, LangGraph or
similar to a new project by default. If an application already has a
CrewAI crew or LangGraph graph, keep it unchanged and wrap it with the
orchestrator adapter (`k9_adapters/crewai/`, `k9_adapters/langgraph/`,
`k9_adapters/claude_agent_sdk/`), which adds K9-AIF governance at its
boundary.

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

**Three-layer decoupling — never violate:** each layer *knows* only the layer
directly below it — not just "doesn't import" it. Router references
Orchestrators only, never Squads or Agents. **An Orchestrator knows only
Squads:** it loads a squad by YAML file and squad id, and never names,
imports, registers or builds an Agent — no agent-name lists (`AGENTS = (...)`),
no `AgentRegistry`/`AgentLoader` in an orchestrator module. Test: *if a
squad's agents change, the orchestrator is unaffected* (only the squad YAML
and the agent's own YAML/class change). Squad YAML has no `orchestrator:`
field; Agent YAML has no `squad:`/`routing:` fields.

**The squad-layer pattern (1.18.1):**

- Squads are **YAML** (`agents:`, `flow:`, `synthesis:`); `BaseSquad` runs
  any of them — a squad needs no `.py` of its own.
- At most **one common `<App>Squad(BaseSquad)`** per application, for
  squad-level behaviour (`before_step(agent_name, context)`, e.g. stop a
  withdrawn job). The loader instantiates it once **per squad**, with that
  squad's agents from its YAML.
- `SquadLoader.from_agents(agents_dir, config, squad_cls=<App>Squad,
  agent_kwargs=...)` is built **once at the app entry point** and passed to
  every orchestrator as `squads=`. It resolves each agent the squad YAML names
  through `AgentLoader` (`class:` + `module:` in the agent YAML).
- In the orchestrator: `self.squads.load_one(squad_yaml, squad_id,
  config=run_config)` — nothing else. `config=` carries a per-run override
  (e.g. a relaxed governance check) without the orchestrator knowing which
  agents it reaches.

Enforced: k9_inspect **K9-DEC-002** (orchestrator names or builds agents →
violation; K9-DEC-001 only catches imports), and
`tests/test_orchestrator_knows_only_squads.py`. Before 1.18.1 the framework's
own `AgentLoader` docstring and the EOC taught registering agents inside the
orchestrator; registering by name (1.15) removed the imports but kept the
coupling — don't copy that pattern from older code.

Cardinality: Router 1→N Orchestrators, Orchestrator 1→N Squads
(`execute_squads(..., parallel=True/False)`), Squad 1→N Agents (sequential
`flow`).

**Squad context (1.16).** Each step gets the full accumulated context unless
the step sets `context_keys` (scoping) or the squad sets `synthesis:`
(`off` default | `auto` | `always`): the squad coordinator then hands the step a
digest (`squad_digest`) from `K9ContextSynthesizerAgent` (a governed
`BaseAgent`) instead of the upstream outputs; full outputs stay in the
squad's results, each digest is logged in `squad_synthesis`. Recipe: `SKILLS.md`
Skill 4. Tests: `tests/test_squad_synthesis.py`.

## LLM calls — one path only

Agents never call `OllamaLLM`/`LLMFactory` **or `ModelRouterFactory`/
`router.invoke()`** directly — only `llm_invoke.py` itself is allowed to
touch the router. Always:

```python
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
resp = llm_invoke(self.config, InferenceRequest(prompt=..., task_type=...))
```

`llm_invoke` raises `RuntimeError` on failure — it never silently returns
empty output (see "Failures propagate" below for who handles it). It also retries on an empty
response (a hybrid-reasoning model burning its whole token budget on
invisible "thinking" and returning 0 chars is a real, observed failure
mode) and emits the `LLMCall` trace event — both silently lost if an agent
calls `router.invoke()` directly instead. Found live in k9chat's
`ChatAgent.execute()` plus four other agents across two example apps
(2026-09-21) — `check-llm-invoke.sh` (see Hooks below) now catches this
automatically on every write/edit. Full chain + adding a new provider:
`SKILLS.md` Skills 2 and 13.

## Failures propagate: Agent → Squad → Orchestrator

**Property:** every failure of an agent (a model call, a tool, a parse) reaches
a layer that records it and decides what happens next. No layer turns a failure
into ordinary output that the flow carries on with. **Test: make one agent's
model call raise; the flow must end as a recorded failure, and no later agent
or package may run on the missing result.**

| Layer | try/except? | What it does with a failure |
|---|---|---|
| Agent | Only to add context or release a resource, then **re-raise** | Never returns `"[WARN] ..."`, `{"reason": "validation_failed"}` or empty output in place of a result |
| Squad | `BaseSquad.execute()` logs the failed step and **re-raises** | Stops the flow; later steps don't run |
| Orchestrator | **Required** around its squad runs (`execute_flow()`) | Records the failure (status `error`, which step, why) so it can be retried; re-raises or returns the error status |
| Process entry point (consumer loop, API) | **Required** | Publishes/returns the error; the process keeps serving |

- `PermissionError` (Shield/Guardian BLOCK) and `RequiresHIL` propagate the
  same way and are caught by the orchestrator for their own handling.
- **No silent handlers:** `except ...: pass` or a handler that neither
  re-raises nor logs and records is a defect. Degrading on purpose (an
  optional retriever is down) must log a warning saying what was skipped.
- **Partial results only where they are a product:** a side report may keep
  what succeeded and mark the rest "not scored" (example: a quality grader
  keeps its deterministic checks when the judge model is down). Never for an
  agent inside a squad flow.
- **Loop agents (1.18.2):** `BaseValidationLoopAgent` records a
  `run_validation()` exception as a step and **re-raises** it
  (`on_tool_error: raise`, the default). `on_tool_error: escalate` routes it
  to a person; `on_tool_error: fail` returns a FAIL result
  (`{"reason": "validation_failed"}`), only for a loop whose FAIL is itself a
  product, never inside a squad flow. Before 1.18.2 FAIL was the default and
  apps overrode `fail()` to re-raise (DAS `utils/loop_errors.py`); that
  override is no longer needed. Test: `test_squad_stops_when_loop_tool_fails`.

**BaseAgent vs K9ValidationLoopAgent vs K9PlanningLoopAgent** — the
generator/scaffold defaults every agent to one-shot `BaseAgent`. Ask per
agent: one-pass answer → `BaseAgent`; iterative convergence on a confidence
score → `K9ValidationLoopAgent`; agent must plan and revise its own steps →
`K9PlanningLoopAgent`. Full recipe: `SKILLS.md` Skill 10.

## Governance

**Governance by construction (1.15).** `BaseAgent.__init_subclass__` wraps
every subclass's `execute()` (sync or async) when the class is defined, so
on every call, with nothing for the agent to do:

1. `assert_governed()` — `NoopGovernance` outside development/test raises
   `PermissionError` before the agent's code runs (`K9_ENV` unset means
   `production`);
2. `governance.pre_process(payload)` — the agent sees the governed payload;
3. the agent's own `execute()`;
4. `governance.post_process(result["output"])` for a dict result with an
   `output` key (other result fields — audit trail — untouched).

A `PermissionError` from governance (Shield BLOCK) propagates to the caller.
**Overriding `execute()` does not bypass it** — the override is wrapped too.
**`execute_stream()` is the second entry point** and is governed the same way:
the request is checked before the first chunk, the complete reply when the
stream ends (a streamed reply blocked at egress has already been sent, so the
caller reports it as stopped). The default yields `execute()`'s output as one
chunk; an agent that streams model output overrides it (async or sync
generator) and is governed automatically. Run an agent only through
`execute()` / `execute_stream()` — other public methods are not entry points.
**Every model call is governed:** `llm_invoke()` / `llm_invoke_stream()` read a
call-path mark (`k9_core/governance/call_context.py`) that agents' entry points
and the adapters' `execute_flow()` set while they run. Inside, the caller's
checks already cover the call; outside (orchestrator, service or script code),
`llm_invoke()` runs the same `security.shield` checks itself and refuses in
production without governance. Call models only through `llm_invoke()`.
A subclass calling `super().execute()` is governed once (a contextvar guard).
`BaseValidationLoopAgent` / `BaseCriticActorAgent` set
`_governs_own_execute = True` (they run pre/post around the loop, on
`result["output"]`) and get the assertion only. Tests:
`tests/test_governance_by_construction.py`.

**Where governance comes from.** `governance=` if passed; otherwise
`governance_from_config(config)`: `security.shield.enabled: true` →
`ShieldGovernance(config)`; `governance.guardian.enabled: true` →
`GuardianGovernance` (Granite Guardian, `on_unavailable` default
`fail_closed`); both → `ChainedGovernance(Shield, Guardian)`, Shield first.
One config setting therefore governs every agent of an application.
Nothing configured → `NoopGovernance` (fine in development/test, refused in
production).

**Adapters.** The CrewAI, LangGraph and Claude SDK orchestrator adapters
run pre/post at their boundary and call `assert_governed()` at the top of
`execute_flow()`.

**Not wrapped:** orchestrator/router logic outside agents (call
`apply_shield()` / `apply_zero_trust()` / `apply_pre_governance()` there), and
`llm_invoke()` called outside an agent. `enforce_governance()` still exists
(it is the same assertion) and is harmless to call.

**The governance hooks on Orchestrator/Router are `async`.** From sync
code use `_run_coro_sync(self.apply_pre_governance(payload))`, never
`asyncio.run()` (fails inside a running event loop). Orchestrators also have
a sync ingress wrapper, `apply_shield(payload)` → `{"allowed", "reason",
"payload"}`. (BaseAgent's automatic wrapper calls the governance backend
directly and resolves an awaitable result safely.)

**Unit tests** default to `K9_ENV=test` (`k9_aif_abb/tests/conftest.py`);
production behaviour is tested explicitly.

## Security / Vulnerability (k9x_Shield) and Zero Trust

Two independent, non-overlapping security layers ship in the framework —
know which one a question is actually about before answering it:

**k9x_Shield** (`k9_security/vulnerability/`) — 15 concrete
`BaseVulnerabilityCheck` subclasses (`checks/`: `InputSizeCheck`,
`PromptInjectionCheck`, `PIIBoundaryCheck`, `PIIRequestCheck`,
`SemanticDriftCheck`, `ToolArgumentCheck`, `ToolAuthorizationCheck`,
`ExecutionGuardCheck`, `HardcodedCredentialCheck`, `MemoryPoisoningCheck`,
`SystemPromptLeakageCheck`, `OutputSanitizationCheck`,
`RequestFrequencyCheck`, `OutboundLinkCheck` (1.14, egress, opt-in:
lookalike / brand-in-subdomain / user@host / IP / punycode links BLOCK,
shorteners and non-allowlisted hosts FLAG), `PaymentDiversionCheck` (1.16.1, ingress:
payment redirection + review bypass + concealment, any two block)), run in order by `VulnerabilityChain`
(`vulnerability_chain.py`), wrapped by `ShieldGovernance`
(`shield_governance.py`) — a concrete `pre_process`/`post_process`
implementation, i.e. a drop-in `governance=` value for any `BaseAgent`/
`BaseOrchestrator`/`BaseRouter`. A `BLOCK`-status check (or a `FLAG` when
`strict=True`) makes `ShieldGovernance` **raise `PermissionError`** — that
raise is the only block signal; there is no return-value sentinel. A `FLAG`
under `strict=False` (the common config) just logs and lets the payload
through unmodified — `ShieldGovernance` never mutates a passing payload.
`fail_open` controls what happens if a check itself raises: `True` →
treated as FLAG, `False` → treated as BLOCK. Unset, it follows `K9_ENV`
(1.19.0): `False` (fail closed) in production, `True` in development/test;
an explicit value wins. Before 1.19.0 it was always `True`, so an input that
made a check throw passed that check unscreened.

**Shield is off in the shipped configuration.** `k9_aif_abb/config/config.yaml`
sets `security.shield.enabled: false` ("SBBs enable and configure in their
own config.yaml"). Since 1.15 a solution that sets `security.shield.enabled:
true` (with check lists) in its config gets `ShieldGovernance` on every agent
automatically (`governance_from_config`); orchestrators/routers still take
`governance=ShieldGovernance(...)` explicitly. Don't tell anyone Shield is on
by default without checking which config is loaded.

**`ShieldGovernance(config)` runs only the checks listed** under
`security.shield.ingress.checks` / `egress.checks`, and takes the *whole*
config (it reads `config["security"]["shield"]`). With `enabled: true` and
no check lists — or passed the shield block itself instead of the whole
config — it builds empty chains, still logs `enabled=True`, and blocks
nothing (verified: a prompt-injection payload passes). Copy the check lists
from the framework's `config.yaml`, and prove it with one injection test.

**The checks are correct and well-tested** (`tests/test_shield_governance.py`).
Every agent runs them around `execute()` (governance by construction, above);
the loop agents run them around `_execute_loop()` on `result["output"]`.

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

**Zero Trust identity (1.14, `k9_security/zero_trust/identity.py`).**
Before 1.14 both `_zero_trust_context()`s read `principal_id`/`roles`/
`tenant_id`/`trust_zone` from the payload — any caller (another agent
included) could claim `roles: ["admin"]`. Now identity comes from a
`BaseIdentityResolver`: `PayloadIdentityResolver` (that same legacy
behaviour, **still the 1.x default**, warns once) or
`SignedIdentityResolver` (`security.identity.mode: signed`): only a
trusted in-process `ctx["identity"]` or an HMAC-signed `_k9_identity`
stamp counts; self-declared fields are ignored; otherwise `anonymous`.
`BaseRouter.admit(payload, credentials)` is the edge: `BaseAuthenticator`
(OOB `ApiKeyAuthenticator`, keys from env via `security.auth.api_keys`;
`OIDCAuthenticator` for any OIDC provider, IdP adapters `keycloak`
(realm + client roles) / `entra_id` / `okta`, all built by
`AuthenticatorFactory` from `security.auth.providers`; extra `k9-aif[oidc]`;
`keycloak_demo.py` verified live)
→ strip claims and any inbound stamp → sign with `$K9_IDENTITY_SECRET`
(same value on every Router/Orchestrator process). Signed mode without the
secret raises when Zero Trust first runs — deliberately, never a silent
fallback to payload. Default flips to signed in 2.0.

**Tool results are governed too (1.14, `k9_security/tool_result_guard.py`).**
What a tool returns is untrusted model input (indirect prompt injection).
`screen_tool_result()` runs it through `governance.pre_process` with the
text under `"query"` (so Guardian reads it). The Claude Agent SDK adapter
does this for every tool automatically (`govern_tool_results=True`;
refused → error notice to Claude); CrewAI tools / LangGraph nodes use
`@govern_tool_result(gov)` / `on_block="raise"`. `can_use_tool` still
governs the outgoing call — the two gates are complementary.

**Security capability catalog** (`k9_security/capabilities.yaml`): every
security control above, mapped to OWASP LLM01-10 / ASI01-10, plus known gaps.
**Update it in the same commit as any security control change** --
`test_security_capabilities.py` fails on a missing Shield check or Guardian
risk, a stale component path, or a `framework_version` that doesn't match
`pyproject.toml` (bump both when releasing). K9X Sentinel
(`k9x-ecosystem/k9x_sentinel`) judges new threats against it daily.

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

## Live context from streams (1.17)

`k9_core/streams` + `k9_streams`: events (`EventEnvelope`) arrive on a
`BaseEventFabric` (`KafkaEventFabric`), pass a `GovernanceEventGate`
(application governance; BLOCK → `state.quarantine()`, content never
applied), and projections (`BaseContextProjection.updates()` →
`ContextUpdate`) fold them into `BaseContextState` (`InMemoryContextState`):
latest value per entity with `as_of`/`age_seconds`/`stale`/source.
Raw source messages become envelopes through a per-topic `BaseEnvelopeMapper` (`streams.mappers`: `auto` default, `debezium`, `log_line`, `native`; `ContextIngest.ingest_raw()` for non-Kafka sources). `ContextIngest` wires it. Agents get it two ways: `BaseOrchestrator(
context_state=...)` injects `live_context` for `payload["live_context_refs"]`
in `execute_squads()`; `ContextMCPServer` serves `get_current`/
`recent_changes`/`query` over MCP. Agents never subscribe to Kafka.
`StreamsFactory.create_gate()` refuses ungoverned streams in production.
Recipe: Developer Guide 15.7. Tests: `tests/test_context_fabric.py`.
Reference app: `k9x-ecosystem/k9x_streams`.

## k9x Origin (1.18)

`k9_origin`: built in like Shield. Agents make one call, `get_current(entity, id)`
(plus `recent_changes`, `query`); `K9Origin` resolves: per-agent scope →
request Shield → live state → read-through to the system of record on a miss
→ verify for `verify_before` steps → flags (quarantined, in_review, conflict,
verification_failed when the system of record could not be reached: 1.19.0)
→ answer Shield. Answers are facts (`as_of`, `version`, `source`, flags); Origin
makes no business decisions — `K9RulesAgent` (+ `K9RulesAdapter` /
`RestRulesAdapter`) decides and raises `RequiresHIL`. Config:
`config/origin.yaml` (`OriginConfig`); build with `OriginFactory.create`;
orchestrators take `origin=`; `OriginMCPServer` serves it. Live state applies
events by source order (shared `merge_update`); `RedisContextState` for
clusters (`volatile-lru`, quarantine pinned). Design:
`docs/roadmap/k9x-origin-design.md`. Tests: `test_k9x_origin.py`,
`test_redis_context_state.py` (needs `K9_TEST_REDIS_URL`).

**1.19.0 behaviour (review fixes):** `llm_invoke()` retries are configurable
(`inference.retry`: `attempts`, `delay_seconds` 60 for an empty reply,
`unreachable_delay_seconds` 5 when the server can't be reached). Origin
answers carry `source_unavailable` when a read-through fails (distinct from
not found). Critic-actor agents re-raise a `critique()` failure by default
(`on_critic_error`). `K9EventRouter`/`IntentOrchestrator` raise without a
message bus. `MonitorFactory.create(config)` uses `config["monitors"]`;
`PersistenceFactory.create()` raises instead of returning `None`.

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

**`K9ModelRouter` learns only from graded evidence.** Rules (capability
+3, latency/cost tier +2, `default_model`) decide until
`record_feedback(prompt, alias, quality)` has supplied graded outcomes;
then a k-NN quality predictor over similar prompts can overrule them by
`learning.margin` points (`k9_inference/learning/`). Before 1.13 the
router stored sessions/decisions/affinity but never read them back --
don't describe older versions as adaptive. Runtime calls record only
success/latency (circuit breaker), not quality: something must grade.
A `confidential` request is hard-restricted to confidential-capable models
(before 1.13 a +3 capability match could beat the +2 confidential score).

## Everything is provisioned through factories

Never instantiate directly in application code: `LLMFactory`,
`ModelRouterFactory`, `AgentRegistry`, `OrchestratorRegistry`,
`SecretManagerFactory`, `CacheFactory`, `ObjectStorageFactory`,
`AuthenticatorFactory` (1.14: `api_key`/`oidc`/`keycloak`/`entra_id`/`okta`;
solutions `register()` their own `BaseAuthenticator`). Every factory
`create(config)` has a zero-config default (env secrets, in-memory cache,
local storage) — no config key required for the common case. Adding a new
provider to any of these: `SKILLS.md` Skill 11.

**Factories are static and hold one configuration per process** (one
application per process; a multi-role app runs each role as its own process
with the same config). The same `inference` config again is a no-op, a config
without an `inference` section uses the process's, a *different* one raises
`ConfigConflictError` (before 1.18.8 the first config silently won, and a
second app or an agent's own `inference:` got the first app's models).
`LLMFactory` resolves a backend **per alias** (`models.<alias>.backend`, then
`llm_factory.backend`, then `ollama`; alias connection keys override the
factory's) and `ModelRouterFactory` refuses a catalog `provider` that differs
from the backend serving its `llm_ref`. Messaging: in production an unreachable
broker raises `MessagingUnavailableError` from `K9EventBus` (and
`MessageFactory`/`BaseComponent` let it through) instead of running on a bus
that drops events; dev/test degrade with a warning. Each app sets its own
`messaging.topic`/`group_id` (the defaults `k9aif-events`/`k9aif-core` warn).
Tests reset with `k9_aif_abb.k9_factories.reset_all()` (autouse in
`tests/conftest.py`). Developer Guide 17.7; tests:
`test_factory_process_safety.py`.

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

**Large events (1.20).** An event over `max_event_bytes` (512 KB) is stored in
object storage (`object_storage` config; bucket `messaging.large_events.bucket`,
default `k9aif-large-events`, objects under `large-events/` expire after
`ttl_days`, default 30) and sent as a link (`k9_large_event`); the bus's
consumers fetch it back and check its sha256, so callbacks get the original
event. Production without `object_storage` raises `LargeEventError`; a failed
upload raises and nothing is sent. Before 1.20 the event was replaced by
`{"truncated": true}`. Send errors raise to the caller. Documents the Router
stores itself (`store_document()` → `document_uri`) are unchanged.
Tests: `tests/test_large_events.py`.

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
| `check-readme-links.sh` | `README.md` | blocks relative links and images (README is the PyPI long description; PyPI 404s them) |
| `check-orchestrator-squads.sh` | `*.py` orchestrators | blocks an orchestrator that names, imports or builds agents (K9-DEC-002) |

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
Nothing is ever wired *in front of* the Router. Below `routing.confidence_threshold`
(default 0.6, one constant for both since 1.19.0) `IntentSquad.on_low_confidence()` fires and
`IntentOrchestrator` asks for clarification.

**Config.** Two levels: the framework's `k9_aif_abb/config/config.yaml`
(test defaults: Ollama, SQLite, Shield off) and each solution's own
`config/config.yaml`, which overrides it. Key sections:
`inference.llm_factory.models`, `inference.model_catalog`,
`inference.router.persistence` (sqlite | postgres | memory), `postgres`,
`messaging`, `security.shield`.

**Persistence.** `RoutingStateStore` (`k9_storage/routing_state_store.py`)
holds `sessions`, `session_turns`, `routing_decisions`, `context_artifacts`,
`hil_pending` and `routing_outcomes` (learned-routing evidence, 1.13) — SQLite auto-created, PostgreSQL by reflection;
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
