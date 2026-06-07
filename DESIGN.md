# K9X StudioX — Agentized Architecture Design

**Title:** K9 StudioX — Built on the K9-AIF Framework  
**Author:** Ravi Natarajan & Claude Code  
**Date:** 2026-06-04  
**Status:** Design Phase

---

## Vision

Rebuild K9X Studio's backend as a proper K9-AIF application — using the same framework it generates scaffolds for. The studio eats its own cooking.

Every HTTP request becomes a Kafka event. Every generation pipeline becomes a Squad. Every file generation becomes a Sub-Agent.

---

## Current State (k9x_studio)

The current backend is a monolithic FastAPI application:

```
backend/api/routes.py          ← all logic in one file (900+ lines)
backend/services/              ← helper functions (not agents)
  scaffold_service.py
  bpmn_service.py
  context_service.py
```

No agents. No squads. No K9-AIF ABB contracts. Pure procedural Python.

---

## Target State (k9x_studiox)

```
K9EventRouter
    │
    ├── SpecImportOrchestrator → SpecImportSquad
    │         ├── GovernanceAgent          GREEN  — screens doc for safety
    │         ├── SpecParserAgent          GREEN  — extracts agents from 3.1.8
    │         │     └── [sub] IntakeExtractorAgent
    │         │     └── [sub] AgentExtractorAgent
    │         │     └── [sub] ZoneMappingAgent
    │         ├── LLMGroupingAgent         AMBER  — groups agents into squads via LLM
    │         ├── ScoringAgent             GREEN  — scores LLM vs rule-based, picks winner
    │         └── CanvasBuilderAgent       GREEN  — builds canvas suggestion JSON
    │
    ├── ScaffoldOrchestrator → ScaffoldSquad
    │         ├── TemplateRendererAgent    GREEN  — renders Jinja2 templates
    │         │     └── [sub] AgentFileAgent       (one per agent, parallel)
    │         │     └── [sub] SquadFileAgent       (one per squad, parallel)
    │         │     └── [sub] OrchestratorFileAgent
    │         │     └── [sub] ConfigFileAgent
    │         └── ZipPackagerAgent         GREEN  — packages all files into ZIP
    │
    ├── BPMNImportOrchestrator → BPMNImportSquad
    │         ├── BPMNParserAgent          GREEN  — parses BPMN XML
    │         ├── LLMGroupingAgent         AMBER  — groups tasks into squads (reused)
    │         └── CanvasBuilderAgent       GREEN  — builds canvas (reused)
    │
    └── LLMOrchestrator → LLMSquad
              ├── LLMVerifyAgent           GREEN  — tests LLM connectivity
              ├── LLMModelsAgent           GREEN  — fetches available models
              └── LLMSuggestAgent          AMBER  — generates architecture from description
```

---

## New ABB: K9SubAgentSpawner

The key innovation — a parent agent that spawns child agents in parallel:

```python
# k9_aif_abb/k9_agents/parallel/k9_sub_agent_spawner.py

class K9SubAgentSpawner(BaseAgent):
    
    def spawn_parallel(self, agent_classes: list, payloads: list) -> list:
        """Spawn multiple sub-agents in parallel, return merged results."""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(cls(config=self.config).execute, payload)
                for cls, payload in zip(agent_classes, payloads)
            ]
            return [f.result() for f in futures]
    
    def spawn_sequential(self, agent_classes: list, payload: dict) -> dict:
        """Spawn sub-agents sequentially, each enriches the shared context."""
        context = dict(payload)
        for cls in agent_classes:
            result = cls(config=self.config).execute(context)
            context.update(result)
        return context
```

**Use case — ScaffoldAgent spawning file generators in parallel:**
```python
class TemplateRendererAgent(K9SubAgentSpawner):
    def execute(self, payload):
        agents = [AgentFileAgent] * len(payload['agents'])
        payloads = [{'agent': a, ...} for a in payload['agents']]
        results = self.spawn_parallel(agents, payloads)
        return {'files': results}
```

---

## Migration Plan

### Phase 1 — Introduce ABB contracts (no behaviour change)
1. Create `k9x_studiox/agents/` folder structure
2. Create agent stubs for each agent in the design
3. Wire `K9EventRouter` to receive HTTP events and dispatch to orchestrators
4. Keep existing services as helper utilities called by agents

### Phase 2 — Replace routes with agent calls
1. Replace `routes.py` functions with `orchestrator.run(event)`
2. Each API endpoint becomes: receive HTTP → emit event → router dispatches → squad runs → return result
3. Introduce `K9SubAgentSpawner` for parallel scaffold generation

### Phase 3 — Full K9-AIF native
1. Kafka as message bus (optional — can keep HTTP for simplicity)
2. Full governance on all agents
3. Observability via K9-AIF monitoring hooks
4. ModelRouter for LLM selection per agent

---

## Folder Structure (target)

```
k9x_studiox/
├── agents/
│   ├── src/
│   │   ├── governance_agent.py
│   │   ├── spec_parser_agent.py        ← K9SubAgentSpawner
│   │   │     sub: intake_extractor_agent.py
│   │   │     sub: agent_extractor_agent.py
│   │   │     sub: zone_mapping_agent.py
│   │   ├── llm_grouping_agent.py
│   │   ├── scoring_agent.py
│   │   ├── canvas_builder_agent.py
│   │   ├── template_renderer_agent.py   ← K9SubAgentSpawner
│   │   ├── zip_packager_agent.py
│   │   ├── bpmn_parser_agent.py
│   │   ├── llm_verify_agent.py
│   │   └── llm_suggest_agent.py
│   └── yaml/
│       └── (one YAML per agent)
├── squads/
│   ├── yaml/
│   │   ├── spec_import_squad.yaml
│   │   ├── scaffold_squad.yaml
│   │   ├── bpmn_import_squad.yaml
│   │   └── llm_squad.yaml
│   └── src/
├── orchestrators/
│   ├── spec_import_orchestrator.py
│   ├── scaffold_orchestrator.py
│   ├── bpmn_import_orchestrator.py
│   └── llm_orchestrator.py
├── config/
│   ├── config.yaml
│   └── squads.yaml
├── backend/
│   ├── main.py           ← FastAPI thin layer, translates HTTP → events → router
│   └── api/
│       └── routes.py     ← minimal, delegates to orchestrators
├── frontend/             ← unchanged React app
└── templates/            ← Jinja2 templates (unchanged)
```

---

## Key Design Decisions

1. **FastAPI stays** — it's the HTTP interface, not the application. Routes become thin wrappers that call `orchestrator.run(event)`.

2. **No Kafka for Phase 1** — direct orchestrator calls. Kafka can be added in Phase 3 for async generation of large scaffolds.

3. **Sub-agent spawning is synchronous in Phase 1** (ThreadPoolExecutor), async in Phase 3.

4. **Existing services become agent utilities** — `scaffold_service.py`, `bpmn_service.py` etc. become private helpers called by agents, not standalone services.

5. **Frontend unchanged** — the agentization is a backend concern only.

---

## Success Criteria

- Every scaffold generation runs through a proper K9-AIF Squad
- SpecParserAgent spawns sub-agents for parallel extraction
- Scaffold files generated in parallel via TemplateRendererAgent sub-agents
- All agents have YAML configs, governance hooks, and observability
- The studio itself becomes a reference implementation of the framework

---

*"The studio that generates K9-AIF applications is itself a K9-AIF application."*
