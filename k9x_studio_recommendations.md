# K9X Studio — Recommendations for State-of-the-Art Agentic Implementation

> Companion to [DESIGN.md](DESIGN.md). DESIGN.md describes *how StudioX itself
> is being agentized* (Phase 2). This document describes what StudioX should
> in turn **recommend to the user** once their project spec has been imported —
> the architecture choices, testing discipline, and governance/inspection
> tooling that make a generated K9-AIF project production-ready rather than a
> demo. The long-term intent is for the Studio to emit a per-project
> `<ProjectName>_recommendations.md` alongside the canvas suggestion and
> generated scaffold — this document is the template for that output and the
> internal checklist for getting there.

---

## 1. Why a recommendations artifact?

Today `/spec/import` (now `SpecImportOrchestrator` → `SpecImportSquad`, see
[DESIGN.md](DESIGN.md)) returns a **canvas suggestion** — orchestrators,
squads, agents, and a zone classification. That answers *"what should the
architecture look like?"*. It does not yet answer the next three questions an
architect always asks:

1. *Which of these agents need to be iterative, parallel, or critic-reviewed —
   and why?*
2. *How do I test this before it touches production data?*
3. *How do I keep it compliant and secure as it evolves?*

A generated `_recommendations.md` closes that gap — it is the artifact that
turns "here's a canvas" into "here's how to build, test, and run this safely".
It should be produced by a new `RecommendationAgent` appended to
`SpecImportSquad`'s flow (`result_key: recommendation`), consuming the same
`parsed` / `scored` / `canvas` context the existing agents already build —
no new parsing, just a synthesis pass over context that already exists.

---

## 2. State-of-the-art agentic patterns — what to recommend per project

These are the structural decisions StudioX should surface for *every* spec it
imports, derived directly from the zone classification already computed by
`ZoneMappingAgent` (see `agents/src/zone_mapping_agent.py`).

### 2.1 BaseAgent vs K9ValidationLoopAgent vs K9CriticActorAgent

This is already encoded in `zone_to_agent_type()`
(`backend/services/spec_parsing_service.py`) — GREEN → `BaseAgent`,
AMBER → `K9ValidationLoopAgent`, RED → `K9CriticActorAgent`. The
recommendations doc should *explain* that mapping per agent, in the spec's own
language, e.g.:

> **FraudSignalAgent** (AMBER) → `K9ValidationLoopAgent`. Fraud correlation
> needs to test a hypothesis, observe a signal, and decide whether to dig
> deeper — a one-shot `BaseAgent.execute()` cannot express that loop. See
> Skill 10 in SKILLS.md for the five methods to implement
> (`generate_hypothesis` → `run_validation` → `evaluate_observation` →
> `should_continue` → `finalize`).
>
> **ComplianceAuditAgent** (RED) → `K9CriticActorAgent`. High-risk decisions
> benefit from an actor/critic refinement pass before being trusted —
> `generate()` proposes, `critique()` challenges (ideally backed by a real
> external validator, not just another LLM call), `refine()` incorporates the
> critique, `should_accept()` gates finalization.

### 2.2 Sub-agent decomposition and parallel spawning

`K9SubAgentSpawner` (new ABB, `k9_agents/parallel/k9_sub_agent_spawner.py`)
is the mechanism StudioX itself now uses — `SpecParserAgent` spawns
`IntakeExtractorAgent` / `AgentExtractorAgent` / `ZoneMappingAgent` in parallel
via `spawn_parallel()`. This is the pattern to recommend whenever a spec
describes an agent whose job is naturally **decomposable into independent
sub-tasks over the same input** — document intake (extract fields + extract
tables + classify zones, as here), multi-source evidence gathering, parallel
template/file rendering (the planned `TemplateRendererAgent` →
`AgentFileAgent`/`SquadFileAgent` fan-out in `ScaffoldOrchestrator`).

Recommendation heuristic to embed in `RecommendationAgent`:

> *"Does this agent's description describe 2+ independent extraction or
> validation steps over the same input, with no data dependency between
> them?"* → recommend `K9SubAgentSpawner.spawn_parallel()`. *"...but step 2
> needs step 1's output?"* → recommend `spawn_sequential()` — same mechanism,
> threaded context, no thread-pool race.

Sizing guidance worth stating explicitly: `ThreadPoolExecutor` parallelism pays
off for **I/O-bound** sub-agents (LLM calls, document parsing, file I/O — the
overwhelming majority of K9-AIF agent work). For CPU-bound transforms on large
payloads, recommend `ProcessPoolExecutor` instead — `K9SubAgentSpawner` can
grow a `spawn_parallel(..., executor="process")` option in Phase 3 without
changing any caller's contract.

### 2.3 Intelligent Model Router — recommend per-agent `task_type`/`model` alignment

Every generated agent gets `model: general | reasoning | ...` from its YAML —
but the *quality* of that choice depends on `K9ModelRouter`'s scoring signals
(`task_type`, `sensitivity`, `latency_budget`, `cost_profile` — see Skill 8 in
SKILLS.md and `k9_inference/routers/k9_model_router.py` `_score_candidate()`).
The recommendations doc should translate the spec's own language into those
signals per agent, e.g.:

| Spec signal | Recommended `InferenceRequest` field | Why |
|---|---|---|
| "real-time", "interactive", "while the customer waits" | `latency_budget="realtime"` | +2 score toward realtime-tier models |
| "confidential", "PII", "regulated data" | `sensitivity="confidential"` | +2 score toward guardian-capable models |
| "high volume", "batch", "cost-sensitive" | `cost_profile="minimal"` | +2 score toward minimal-cost-tier models |
| RED-zone / compliance / audit | `task_type="reasoning"` + `sensitivity="confidential"` | stacks scoring signals for the most capable, governed model |

If the imported spec implies routing needs `K9ModelRouter` doesn't cover
(cost optimization across providers, A/B testing, compliance-mandated
provider pinning), recommend extending `BaseModelRouter` per Skill 3 — the
rest of the stack (agents, squads, orchestrators) is unaffected by that swap.

### 2.4 Squad shape — when to split, when to merge

`build_suggestion_from_zones()` already proposes an `OperationsSquad`
(GREEN) + `IntelligenceSquad` (AMBER/RED) split. Recommend going further when
the spec describes **clearly sequential workflow stages within a zone** —
e.g. intake → triage → adjudication is three GREEN stages that may still
warrant separate squads (and separate orchestrators) if they have different
SLAs, different failure-handling needs, or are meant to be independently
deployable/scalable. The decoupling rule (squad knows its agents and flow
only; orchestrator is the caller) makes this split free — no agent code
changes, just YAML.

---

## 3. Testing discipline to recommend

Generated projects ship with stub tests (Skill 6 — mock `llm_invoke`, never a
live model). The recommendations doc should turn that generic guidance into a
**per-agent test checklist** derived from the canvas suggestion:

1. **Every agent** — unit test `execute()` with `llm_invoke` mocked
   (`unittest.mock.patch`), asserting the output schema declared in its YAML
   is honored. This is mechanical and can itself be agent-generated — a
   `TestStubAgent` that reads `output_schema:` from each generated agent YAML
   and emits a parametrized pytest skeleton is a natural Phase-3 addition to
   `ScaffoldOrchestrator`.
2. **K9ValidationLoopAgent / K9CriticActorAgent agents** — test the
   *disposition* transitions (`CONTINUE → FINALIZE/ESCALATE/FAIL`), not just
   the final output. Mock `run_validation`/`critique` to return controlled
   observations and assert `should_continue()` / `should_accept()` make the
   right call at the right confidence thresholds.
3. **K9SubAgentSpawner subclasses** — test `spawn_parallel`/`spawn_sequential`
   merge logic with stub child agents (no thread pool needed — substitute
   simple callables that return canned dicts) to verify result-ordering and
   context-merging are correct independent of LLM behavior.
4. **Squad flow** — `bash test_squads.sh` pattern (already in CLAUDE.md
   Commands) generalizes: assert the `when:` gating actually skips steps when
   governance fails, and that `result_key`s land where downstream agents
   expect them. StudioX's own `SpecImportSquad` smoke test is the template:
   route a sample doc through `K9EventRouter` directly (no HTTP, no LLM) and
   assert on `governance.passed`, `parsed.zone_groups`, `canvas.source`.
5. **End-to-end** — `test_model_router.sh` pattern: one real-LLM run per
   squad, gated behind an environment check (skip if Ollama/endpoint
   unreachable), to catch prompt/schema drift that mocks can't.

Recommend wiring all of the above into the generated project's
`run_<app>.sh` / CI as a `pytest k9_projects/<App>/tests/ -v` step before any
`k9_generator.sh run` smoke test — cheap, fast, catches the majority of
integration breakage before a model is ever invoked.

---

## 4. Governance & inspection tooling to recommend

### 4.1 `k9_inspector` — architectural compliance, not security scanning

Per the long-term `k9_code_review` vision (already scaffolded as
`/k9aif:inspect` in `k9aif-plugin/`), `k9_inspector`'s mandate
is **SBB-vs-ABB compliance**: does this generated project actually follow the
contracts it claims to extend? Concretely, for a StudioX-generated project,
`k9_inspector` should check:

- Every agent extends `BaseAgent` (or the correct zone-appropriate subclass —
  flag a GREEN-zone agent class extending `K9CriticActorAgent` as
  over-engineered, and an AMBER/RED agent extending plain `BaseAgent` as
  under-governed)
- Squad YAML carries no `orchestrator:` field; agent YAML carries no
  `squad:`/`routing:` fields (the decoupling rule — both directions)
- Agents call `llm_invoke()` exclusively, never `OllamaLLM`/`LLMFactory`
  directly (Skill 2)
- `enforce_governance()` is present in any agent whose YAML declares
  `governance.pre_process: true` and whose zone is AMBER/RED
- `K9_ENV` is never hardcoded to `development`/`test` outside of test files
- Factory usage — no direct instantiation of routers/registries that should
  come from `LLMFactory` / `ModelRouterFactory` / `AgentRegistry` /
  `OrchestratorRegistry`

This is **pattern-fitness inspection**, run *after* generation, against the
scaffold `k9_generator.sh` produced — exactly the gap the long-term
`k9_inspector` vision is meant to fill. StudioX's `RecommendationAgent`
should append a line pointing the user at it: *"Run `k9aif:inspect
k9_projects/<App>` after generation to verify ABB compliance before your
first commit."*

### 4.2 `k9_vulnerabilityTest` — a distinct, currently-missing capability

This is **not** what `k9_inspector` does, and should not be folded into it —
they answer different questions:

| | `k9_inspector` | `k9_vulnerabilityTest` (proposed) |
|---|---|---|
| Question | "Does this code follow K9-AIF architectural contracts?" | "Can this running system be made to misbehave?" |
| When it runs | Static — against generated source, pre-deploy | Dynamic — against a running instance, pre-/post-deploy |
| Domain | ABB/SBB pattern fitness, decoupling, governance wiring | OWASP Top 10, prompt injection, governance bypass, zone-escalation |

**Recommendation: scaffold `k9_vulnerabilityTest` as a new K9-AIF agent
squad** (eat-your-own-dog-food, same as StudioX itself) rather than a
bespoke script — it is squarely an *iterative validation* problem
(`K9ValidationLoopAgent` is the natural fit: hypothesize an attack →
run it → observe the response → escalate or refine). A first-pass squad:

```yaml
squads:
  VulnerabilityTestSquad:
    description: "Probes a running K9-AIF instance for governance and zone-escalation weaknesses."
    agents:
      - PromptInjectionProbeAgent      # AMBER — mirrors GovernanceAgent's _INJECTION patterns, but actively crafts variants
      - GovernanceBypassProbeAgent     # AMBER — attempts to reach AMBER/RED-zone agents through GREEN-zone entry points
      - ZoneEscalationProbeAgent       # RED  — K9CriticActorAgent: attempts to make a BaseAgent perform K9CriticActorAgent-class actions
      - DependencyAuditAgent           # GREEN — checks requirements.txt / pyproject.toml against known-CVE feeds
      - VulnerabilityReportAgent       # GREEN — assembles findings into a scored report (mirrors ScoringAgent's pattern)
    flow:
      - agent: PromptInjectionProbeAgent
        result_key: injection_probe
      - agent: GovernanceBypassProbeAgent
        result_key: bypass_probe
      - agent: ZoneEscalationProbeAgent
        result_key: escalation_probe
      - agent: DependencyAuditAgent
        result_key: dependency_audit
      - agent: VulnerabilityReportAgent
        result_key: report
```

**Critical design constraint — this is offensive tooling against your own
deployments only.** Every probe agent must:

- Run only against `K9X_PROJECTS_ROOT`-contained, explicitly-named local
  instances — never accept an arbitrary URL (mirror the `_is_local_blocked`
  / path-containment discipline already in `routes.py`)
- Require an explicit `--i-own-this-instance` style confirmation flag, logged
  and audited, before any probe agent executes
- Default to `K9_ENV=development`/`test` only — refuse to run with
  `enforce_governance()` raising in production, by design
- Never be wired with a `message_bus` that could leak probe payloads onto a
  shared Kafka topic

This keeps it squarely in **defensive/authorized-testing** territory — a tool
a solutions architect runs against their own staging environment before
go-live, structurally identical to a pentest engagement scoped to assets you
own. It is an excellent Phase-3 candidate precisely because the squad/agent
machinery to build it (`K9ValidationLoopAgent`, `K9CriticActorAgent`,
`K9SubAgentSpawner` for running probes in parallel) now all exists in the
framework — and, after this phase, in StudioX itself.

### 4.3 Governance — recommend per-zone, not blanket

`require_governance()` already differentiates `development`/`test`
(NoopGovernance + WARNING) from `production`/`staging`
(`enforce_governance()` raises). The recommendations doc should call out,
per AMBER/RED agent identified by `ZoneMappingAgent`, that
`enforce_governance()` must be the first line of `execute()` — and flag it as
a launch blocker, not a nice-to-have, exactly the way `k9_inspector` (§4.1)
would catch it mechanically.

---

## 5. Implementation note for `RecommendationAgent`

Add it as the **sixth and final** step of `SpecImportSquad`'s flow
(`agents/yaml/recommendation_agent.yaml` +
`agents/src/recommendation_agent.py`, GREEN — pure synthesis, no LLM call
required for v1 since every input it needs — `zone_groups`, `agents_raw`,
`canvas.suggestion` — is already in context by the time it runs):

```yaml
      - agent: RecommendationAgent
        result_key: recommendations
        when:
          key: governance.passed
          eq: true
```

`CanvasBuilderAgent` then includes `recommendations` (a markdown string) in
its packaged response, and the frontend offers it as a downloadable
`<ProjectName>_recommendations.md` alongside the canvas — the same
"transparent, inspectable artifact" philosophy that already governs the
canvas suggestion and scoring breakdown.

A v2 worth considering once `LLMGroupingAgent`'s pattern is proven: let
`RecommendationAgent` make **one** LLM call (AMBER) to turn the mechanically
generated checklist into spec-specific prose — "why *this* project's
FraudSignalAgent specifically needs a validation loop" rather than a generic
template paragraph. Score it the same way `ScoringAgent` scores groupings
(does the LLM version reference more spec-specific detail than the
rule-based version?) — consistent with the "LLM proposes, deterministic
logic verifies" philosophy already proven out in `SpecImportSquad`.
