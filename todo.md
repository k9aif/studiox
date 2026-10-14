# TODO: Streams and k9x Origin in Studio

Goal: when a requirements document describes live data (events, current status, changes
arriving from other systems), Spec Import plots the data flow on the canvas, and Generate
Scaffold produces a project that runs it on the framework's context fabric and k9x Origin
(k9-aif 1.17 and 1.18).

Today Studio knows none of this: the palette (`backend/api/routes.py` `PALETTE`) has no
live-data component, `K9RulesAgent` is not an agent type, and the scaffold never writes
`config/origin.yaml` or passes `origin=` to orchestrators. The only mention is the framework
CLAUDE.md copied into every scaffold (`context/CLAUDE.md`).

Reference: K9X Streams (`k9x-ecosystem/k9x_streams`, streams.k9x.ai) is the working example of
everything below; framework design note `k9-aif-framework/docs/roadmap/k9x-origin-design.md`;
Developer Guide 15.7 (context fabric) and 15.8 (Origin).

---

## 0. Prerequisites

- [ ] k9-aif 1.18.1 on PyPI (scaffolds and Studio itself now require it). Rebuild studio.k9x.ai only after.
- [ ] `squads/yaml/spec_import_squad.yaml` header still says the orchestrator owns the squad "via `_load_squad()`"; reword to the squad layer (loaded by id through `squads=`).

## 1. What the canvas should show

The flow in K9X Streams, as canvas nodes:

```
Source systems ──► Kafka topics ──► Shield gate ──► Projections ──► Live state ──► k9x Origin ◄── agents
 (ERP, CDC, IoT)    (per entity)    (quarantine)    (event → entity)  (memory/Redis)  (one call)     (get_current)
                                                                                         │
                                                                         read-through / verify ──► system of record
```

Placement (one graph, viewed by layer, as `canvasLayers.ts` already does):

- [ ] A **Live data band** below the execution columns, left to right: sources → topics → gate →
      projections → live state → Origin. It is a data plane shared by all orchestrators, so it
      sits under them rather than in the Router → Orchestrator → Squad → Agent columns.
- [ ] Edges from the execution layers into the band:
  - squad → Origin: `live_context` (the entities the squad receives before it runs);
  - agent → Origin: `get_current` / `recent_changes` (the agent's `allowed_entities`);
  - Origin → system of record (an existing API / data adapter node): read-through and `verify_before`.
- [ ] Conflict path: Origin → Business Rules step (`K9RulesAgent`) → HIL Orchestrator when a rule
      says so (e.g. approved then disapproved within a window, claim over a limit).
- [ ] New canvas sub-tab **Live data** in `canvasLayers.ts` (filter, not a second layout).
- [ ] `LEVEL_X` / layout: a row (y band) for the live-data nodes; keep the existing columns unchanged.

## 2. Model: new component types

- [ ] `types.ts` `ComponentType`: `event_source`, `event_topic`, `stream_gate`, `projection`,
      `live_state`, `origin` (singleton, like `router`).
- [ ] `AgentClassType`: add `K9RulesAgent` (business rules; rules YAML or a REST decision service).
- [ ] `PALETTE` entries (`routes.py`) with `abbClass`: `KafkaEventFabric`, `GovernanceEventGate`,
      `BaseContextProjection`, `InMemoryContextState` / `RedisContextState`, `K9Origin`, `K9RulesAgent`.
- [ ] Node properties:
  - Origin: entities (key, system of record, owned fields, conflict watches), sources
    (mcp / api / sql, pointing at existing adapter nodes), topics, governance (request/answer checks);
  - Live state: memory or Redis (maxmemory, volatile-lru);
  - Topic: mapper (`auto`, `debezium`, `log_line`, `native`);
  - Squad: `live_context` refs (e.g. `invoice:{invoice_id}`), `verify_before` steps;
  - Agent: `allowed_entities`.
- [ ] `rules.ts` / `studio_rules.md`: Origin states facts, never decisions (decisions go to a
      Business Rules step); only Router and Orchestrator publish to Kafka; one Origin per app.

## 3. Spec Import: find live data in the requirements document

Pipeline today: Governance → SpecParser (Intake / Agent / Zone sub-agents) → LLMGrouping →
Scoring → CanvasBuilder.

- [ ] New sub-agent `LiveDataExtractorAgent` (SpecParser sub-agent, GREEN, deterministic first, LLM
      suggestion second, same split as grouping vs scoring). Signals:
  - events and feeds: "event", "stream", "Kafka", "topic", "CDC", "change data", "webhook", "IoT", "telemetry";
  - currency: "current status", "real time", "latest", "as of", "up to date", "stale";
  - entities whose state changes: invoice, claim, payment, order, shipment, vendor, account;
  - reversals and races: "approved then", "cancelled after", "duplicate payment", "out of order";
  - systems of record named in the document (ERP, SAP, core banking, policy admin).
- [ ] Output: entities (name, key, system of record), event sources and topics, which steps need
      current data, which steps are irreversible (`verify_before` candidates), conflict rules.
      Each item carries the sentence it came from (provenance), shown on the node.
- [ ] `CanvasBuilderAgent`: place the band (section 1) only when the extractor found live data;
      otherwise the canvas is unchanged.
- [ ] Scoring: the deterministic extraction is the baseline; the LLM's suggestion is compared to it,
      as with squad grouping.
- [ ] Sample requirement docs for tests: Accounts Payable (duplicate payment, as in K9X Streams),
      insurance claims (approved then disapproved), one with no live data (must not grow a band).

## 4. Generate Scaffold

- [ ] `config/origin.yaml` from the Origin node (entities, sources, topics, squads, agents, governance).
- [ ] `main.py`: `OriginFactory.create(config, ...)` next to `SquadLoader.from_agents(...)`; pass
      `origin=` and `squads=` to every orchestrator.
- [ ] Ingest worker when topics exist: `KafkaEventFabric` + `GovernanceEventGate` + generated
      projection stubs (one per entity) + `ContextIngest`; `StreamsFactory` for state (memory/Redis).
- [ ] Optional `OriginMCPServer` (or `register_on` an existing MCP server node).
- [ ] Business Rules agents: `K9RulesAgent` + `rules/*.yaml` stub per rules node.
- [ ] Requirements extras: `k9-aif[kafka]`, `[redis]` when chosen.
- [ ] Generated project runs in memory mode with no Kafka (a sample event script fills live state),
      like K9X Streams' generator.

## 5. BPMN import (later)

- [ ] Message start events, intermediate message events and data stores on a process map to
      topics, sources and live state; a gateway that checks current status maps to `verify_before`.

## 6. Tests and docs

- [ ] Spec Import: the three sample docs (live data plotted / not plotted; provenance present).
- [ ] Scaffold: generated project with an Origin node passes `k9aif inspect` (incl. K9-DEC-002) and
      answers `get_current` in memory mode.
- [ ] Studio landing / Arch Guide tab: a short "Live data" section linking to streams.k9x.ai.

## Open questions for Ravi

1. Band placement: below the execution columns (proposed) or a left-hand data column before the Router?
2. Show projections as nodes, or fold them into the topic node (fewer boxes)?
3. Spec Import: deterministic signals only at first, or LLM suggestion from the start?
4. One Origin per application always, or per business domain when a doc has several?
