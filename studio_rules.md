# studiox Architecture Rules

Canonical classification rules for what belongs on a K9-AIF canvas and why. This consolidates
what currently only lives as UI text (`frontend/src/components/ArchGuidePanel.tsx`, the Arch Guide
tab) plus what's actually true in the classification code
(`backend/services/bpmn_service.py`), so it can be checked against — code and UI should agree with
this file; if one drifts, fix the drift, don't let this file silently go stale.

Source of truth for each section is named inline. Anything marked **GAP** is a known place where
current behavior doesn't yet match the rule — not a description of what's built, a description of
what should be, with the gap stated plainly.

## 1. The architecture gate — classify before you build

Source: `ArchGuidePanel.tsx` (Arch Guide tab), verbatim.

**Use Agentic AI when:**
- Input is unstructured — text, images, ambiguous events
- Decision requires reasoning under uncertainty
- Success criteria are subjective or context-dependent
- The plan must adapt dynamically mid-execution
- Competing options need nuanced trade-off analysis
- Recovery from unexpected failure requires judgment
- The task involves synthesising information from many sources

**Use an Adapter (deterministic) when:**
- Input is structured and rules are fully defined
- Same input always produces the same output
- A workflow / BPM / rules platform already owns this logic
- LLM latency or cost is prohibitive at this step
- Auditability requires an exact, explainable trace
- MuleSoft, TIBCO, Appian, Drools, or IBM ODM handles it today
- The logic can be written as deterministic code right now

**Hybrid pattern (most real systems):** the Router classifies incoming events. Fully deterministic
events go directly to an Adapter — no LLM involved. Complex or ambiguous events route to an
Orchestrator that freely mixes Squads (agentic) and Adapters (deterministic) in the same pipeline.

```
Event → Router → Adapter (deterministic)
              or → Orchestrator → Squad + Adapter
```

**Anti-patterns to avoid:**
- Routing every event through an LLM "just to be safe"
- Wrapping a simple REST call in a ValidationLoop agent
- Replacing a rules engine with a prompt that mimics it
- Using agents for batch ETL with no decision-making
- Building 10+ agents when 2 agents + 1 adapter suffice
- Calling an LLM for structured data that a SQL query handles

**Quick classification table:**

| Question | Answer |
|---|---|
| Is the input structured? | → Adapter |
| Are the rules fully deterministic? | → Adapter |
| Requires judgment or reasoning? | → Agent |
| Can a human write the logic today? | → Adapter / Rules |
| Plan changes on interim results? | → Agent |
| Existing platform owns this step? | → Adapter |
| Output must be auditable & exact? | → Adapter |
| Task involves ambiguity or context? | → Agent |

**Principle:** Agents handle uncertainty. Adapters handle certainty. Build cheap deterministic
paths first; only reach for an LLM when the problem genuinely requires reasoning.

## 2. Component taxonomy

Source: `frontend/src/types.ts` (`ComponentType`), `backend/services/bpmn_service.py`.

| Component | Role | Notes |
|---|---|---|
| Router (`K9EventRouter`) | Routes events by `event_type` to the right orchestrator | Singleton |
| Orchestrator | Coordinates squad execution for a domain workflow | One per BPMN lane (or subprocess group / flat-task fallback) |
| **HIL Orchestrator** | **A separate orchestrator kind, event-driven, triggered by human actions via Kafka — not by the Router.** See §4. | Singleton; teal `#14b8a6` |
| Squad | Executes a defined `flow` of agents in sequence | One per lane that produced at least one agent |
| Agent | `BaseAgent` (one-shot) / `K9ValidationLoopAgent` (iterative validate/escalate) / `K9CriticActorAgent` (actor-critic refinement) | Selected by zone, see §3 |
| Adapter | Deterministic, no LLM. Types: `api_adapter`, `rules_adapter`, `workflow_adapter`, `process_adapter`, `bpm_adapter`, `data_adapter`, `messaging_adapter` | Generates **no executable code** today — documented in `ARCHITECTURE.md` only, drawn on canvas only. See plan.md "Known bugs" #4. |

## 3. Zone → agent type (verified, 2026-09-10, this session)

Source: `bpmn_service.py::_agent_type()`, `zone_to_agent_type()` (`spec_parsing_service.py`).

| Zone | Agent Base Type | Meaning |
|---|---|---|
| GREEN | `BaseAgent` (or, more often, an Adapter — deterministic tasks are adapter-classified by BPMN tag/name *before* zone is even consulted) | Fully automated |
| AMBER | `K9ValidationLoopAgent` | Human review before the workflow proceeds |
| RED | `K9CriticActorAgent` | Dual approval required, cannot be overridden |

Zone is read from the BPMN task's own fill color (Process Studio's convention) and is
**authoritative** — it overrides the name-keyword fallback heuristic (`validat`/`review`/`audit`/...
→ `K9ValidationLoopAgent`; `generat`/`draft`/`critique`/... → `K9CriticActorAgent`) that only
applies when no zone color is present.

Adapter-vs-agent classification is a **separate, earlier** decision (BPMN tag or name-hint based),
not zone-driven — a task can be AMBER zone and still adapter-classified if it's tagged as a rule/
service task (e.g. the deterministic three-way-match attempt inside an otherwise-AMBER lane, see
plan.md's "AMBER lanes have two tasks each" note). These two dimensions are complementary, not in
conflict.

## 4. HIL Orchestrator — rules and current gap

**Rule (Ravi, 2026-09-10): HIL is a separate orchestrator**, not a squad or agent attribute bolted
onto an existing one. Confirmed in code (`Canvas.tsx`, manual drag-drop path): a HIL Orchestrator
wires to the **Kafka message bus directly, not the Router** — it's event-driven, triggered by a
human action, not by an incoming process event. It owns its own squad/agent pair for
post-human-action processing.

**GAP, confirmed 2026-09-10:** nothing in BPMN import (`bpmn_service.py`) or the mapping document
(`build_mapping_document()`) creates or wires a HIL Orchestrator automatically. Today a HIL
Orchestrator only exists if a user manually drags it from the palette onto the canvas, where it
auto-creates a **generic placeholder** `HILSquad`/`HILAgent` pair (label literally `"HILSquad"`,
`"HILAgent"`, `model: general`) — not derived from any imported process's actual AMBER/RED
agents, HITL roles, or zone data. The mapping document *does* capture HITL touchpoints as
descriptive text per row (`hitl_touchpoint` column) — nothing yet turns that into an actual wired
HIL Orchestrator node.

**Implication for Step 6** (plan.md, tabbed multi-flow canvas): a "HIL" tab needs an actual HIL
Orchestrator on the canvas to show, wired to the real AMBER/RED squads' escalation paths — not
just a filtered view of the same nodes. This is a real design/build item, not just a display
filter. Open questions to resolve before building it:
- Does every AMBER/RED squad get its own HIL Orchestrator, or one shared HIL Orchestrator per
  process, fanned in from all AMBER/RED squads?
- What does "post-human-action processing" (the HILAgent's stated role today) actually do for a
  process like the AP invoice example — resume the paused squad, or something distinct?

## 5. API adapters specifically

Source: `bpmn_service.py::_ADAPTER_TAG_MAP` / `_ADAPTER_NAME_HINTS`.

`api_adapter` is one of the 7 adapter types, for tasks that call an external REST/GraphQL endpoint
with no LLM inference — matched by BPMN tag (`servicetask`) or name hints (`api`, `rest`,
`graphql`, `endpoint`, `http`, `fetch`, `invoke`, `call`). In the AP invoice example:
`ReceiveDigitizeInvoiceAdapter`, `PostPaymentToLedgerAdapter`, `ExecutePaymentAdapter`,
`GenerateApAgingAnalyticsAdapter` all classified as `api_adapter`. Like all adapters (§2), these
generate no executable code today — canvas/`ARCHITECTURE.md` only.
