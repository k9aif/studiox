# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@SKILLS.md

---

## Hooks

Five PostToolUse hooks fire automatically after every Write or Edit (configured in `.claude/settings.json`):

| Hook | Triggers on | What it checks |
|---|---|---|
| `check-python.sh` | Any `*.py` file | Python syntax (`py_compile`) — exits 2 (blocks) on error |
| `check-yaml.sh` | Any `*.yaml` / `*.yml` | YAML parse validity — exits 2 (blocks) on error |
| `run-abb-tests.sh` | Files under `k9_aif_abb/` | Runs `test_framework.py` + `test_intelligent_model_router.py` |
| `check-governance.sh` | `*.py` under `examples/` | Warns if `NoopGovernance` appears in example code |
| `check-init-docstring.sh` | Any `__init__.py` | Warns if module docstring is missing (required for pydoc generation) |

Hook scripts live in `.claude/hooks/`. Exit code 2 = block the action; exit 0 = continue.

---

## Commands

### Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run tests

All framework stability tests (no external services needed):
```bash
cd k9_aif_abb
pytest tests/test_framework.py -v
pytest tests/test_intelligent_model_router.py -v
```

Single test file:
```bash
pytest k9_aif_abb/tests/test_agent_registry.py -v
```

All tests:
```bash
pytest k9_aif_abb/tests/ -v
```

### Run example apps (local, Mac)

```bash
./run_k9chat.sh
./run_acme_support_center.sh
```

### EOC — build and run (RHEL / Podman)

```bash
bash build.sh                    # build container image only
bash run_eoc_pod.sh              # build + create pod + start 3 containers
sudo podman pod ps               # check pod status
sudo podman logs eoc-app-backend # tail a container
sudo systemctl restart cloudflared  # restart Cloudflare tunnel after deploy
```

After a `git pull` on RHEL, always rebuild (`run_eoc_pod.sh`) — restarting containers alone does not pick up code changes.

### Smoke tests

```bash
bash test_model_router.sh        # router + LLM end-to-end
bash test_squads.sh              # squad execution flow
```

### Generate stub app

```bash
./k9_generator.sh preview <AppName>
./k9_generator.sh run <AppName>
./k9_generator.sh recycle <AppName>
```

---

## Architecture

### Core concept: ABB vs SBB

**Architecture Building Blocks (ABB)** — abstract contracts in `k9_aif_abb/`. Define interfaces, lifecycle, governance hooks. Never contain domain logic.

**Solution Building Blocks (SBB)** — concrete implementations that extend ABBs with domain-specific behavior without modifying the core. Two locations:
- `examples/<AppName>/` — hand-crafted reference SBBs (EOC is the canonical example)
- `k9_projects/<AppName>/` — stub SBBs scaffolded by `k9_generator.sh`; flesh out from the reference examples

### Execution hierarchy

```
Event → K9EventRouter → Orchestrator → Squads → Agents → LLM
```

- **Router** (`k9_core/router/base_router.py`) — routes events by `event_type` to the right orchestrator
- **Orchestrator** (`k9_core/orchestration/base_orchestrator.py`) — coordinates squads for a domain workflow
- **Squad** (`k9_squad/base_squad.py`) — executes a defined `flow` of agents in sequence
- **Agent** (`k9_core/agent/base_agent.py`) — implements `execute(payload) -> dict`; must extend `BaseAgent`

### Inference pipeline

Agents call LLMs exclusively through:

```python
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
resp = llm_invoke(self.config, InferenceRequest(prompt=..., task_type=...))
```

`llm_invoke` → `ModelRouterFactory.get_router()` → `BaseModelRouter.route()` → `LLMFactory.get(llm_ref)` → `OllamaLLM.invoke()`

`K9ModelRouter` is the OOB default implementation of `BaseModelRouter`. Solutions can substitute their own router by implementing `BaseModelRouter` (`k9_inference/routers/base_model_router.py`) and registering it via `ModelRouterFactory`.

`K9ModelRouter` selects the model via weighted scoring:
- `+3` task_type matches a model's `capabilities[]`
- `+2` sensitivity == "confidential" and model has "confidential" capability
- `+2` `latency_budget` matches model's `latency_tier`
- `+2` `cost_profile` matches model's `cost_tier`

Falls back to `default_model` when nothing scores > 0. Selected model, `complexity_score`, and `governance_score` are persisted to the routing state store after every call.

### Governance

Every agent receives a governance pipeline via `require_governance()` at init time.
- In `development`/`test` (`K9_ENV`): NoopGovernance with WARNING log — permitted
- In `production`/`staging`: NoopGovernance with ERROR log — `enforce_governance()` will raise `PermissionError`

Agents that must enforce governance call `self.enforce_governance()` at the top of `execute()`. Agents that skip this call will silently use NoopGovernance even in production.

### Three-level decoupling

Each layer knows only what is **below** it in the hierarchy:

| Layer | Knows about | Does NOT know about |
|---|---|---|
| **Orchestrator** | Its squad ID — loaded via `_load_squad()` | Routers, other orchestrators |
| **Squad** | Its agents and their execution flow | Orchestrators |
| **Agent** | Its own behavior (role, goal, model) | Squads, routing, next agent |

**Squad YAML has no `orchestrator:` field.** The orchestrator is the caller — the squad must not reference its caller.

**Agent YAML has no `squad:` or `routing:` fields.** Agents are squad-agnostic and can be reused across different squads.

### Squad definition (YAML)

Each squad lives in its own YAML file under `squads/yaml/`. Flow steps **must** be dicts with an `agent:` key — plain strings will raise `ValueError` at runtime.

```yaml
squads:
  ClaimsProcessingSquad:
    description: "Triage, adjudication and audit for claims."
    agents:
      - ClaimsTriageAgent
      - AdjudicationAgent
      - GuardAgent
      - AuditAgent
    flow:
      - agent: ClaimsTriageAgent
        result_key: triage
      - agent: AdjudicationAgent
        result_key: adjudication
      - agent: GuardAgent
        result_key: guard
      - agent: AuditAgent
        result_key: audit
```

`SquadLoader` reads this YAML and wires agents from `AgentRegistry` at startup. The orchestrator that calls `_load_squad()` determines which squad runs — that association lives in orchestrator code, not in the squad YAML.

### Config structure (`config.yaml`)

Two levels:
- **Framework ABB config** (`k9_aif_abb/config/config.yaml`) — defaults for testing; Ollama at `<LAN_HOST_IP>:11434`, SQLite persistence
- **Example SBB config** (`examples/<App>/config/config.yaml`) — overrides for that app; EOC uses PostgreSQL (`eoc` schema), Kafka at `<LAN_HOST_IP>:9092`

Key config sections: `inference.llm_factory.models` (maps alias → Ollama model name + params), `inference.model_catalog` (maps alias → capabilities/tiers), `inference.router.persistence` (sqlite | postgres | memory), `postgres`, `messaging` (Kafka/Redpanda).

### Persistence

- **Routing state store** (`k9_storage/routing_state_store.py`) — 4 tables: `sessions`, `session_turns`, `routing_decisions`, `context_artifacts`. SQLite OOB (auto-created); PostgreSQL via reflection. All tables live in the `k9aif` schema on the shared PostgreSQL instance at `<LAN_HOST_IP>`.
- **PostgresDatabaseStorage** sets `search_path` and `MetaData(schema=...)` from `postgres.schema` in config — schema must match the PostgreSQL schema or reflection will miss the tables.

### EOC example structure

`examples/K9X_Enterprise_Insurance_OperationsCenter/` is the canonical reference example.

Three processes (one container each in the pod):
1. `start_eoc_app.sh` — FastAPI backend + Web UI (port 8000)
2. `start_eoc_orchestrator.sh` — Kafka consumer → squads/agents → publishes results to `eoc-results` topic
3. `start_eoc_router.sh` — Kafka router: consumes `eoc-events`, **publishes** to domain topics (`eoc-claims`, `eoc-fraud`, …) by `event_type`

**Kafka publish/subscribe ownership** — by convention, only the Router and Orchestrator process touch Kafka:
- **Router** is the only Kafka publisher for domain topics
- **Orchestrator process** consumes domain topics and publishes to `eoc-results`
- **Agents** are constructed without a `message_bus` in standard K9-AIF solutions — `publish_event()` reaches the monitor and logger only. A2A via Kafka is architecturally possible (wire an agent with a `message_bus`) but is not used in standard solutions — agents share data sequentially through the Squad flow instead

Static assets (`webui/`) use `?v=N` cache busting on own files. Bump the version number when changing `app.js` or `styles.css` and rebuild the container.

### Key ABB contracts

| File | Contract |
|---|---|
| `k9_core/agent/base_agent.py` | `execute(payload: dict) -> dict` — synchronous, must be implemented |
| `k9_core/orchestration/base_orchestrator.py` | `run(event)` — coordinates squad execution |
| `k9_core/router/base_router.py` | `route(event_type)` — returns orchestrator |
| `k9_squad/base_squad.py` | `run(context)` — executes `flow` steps in order |
| `k9_inference/routers/base_model_router.py` | `route(request)` → `RouteDecision`; `invoke(request)` → `InferenceResponse` |
| `k9_core/governance/pipeline.py` | `require_governance()` factory; `NoopGovernance`; `GovernanceConfigError` |
| `k9_agents/validation/base_validation_loop_agent.py` | Iterative loop ABB — `generate_hypothesis` · `run_validation` · `evaluate_observation` · `should_continue` · `finalize` |
| `k9_agents/validation/k9_validation_loop_agent.py` | OOB LLM-driven loop — extend and override only what differs (analogous to `K9ModelRouter`) |
| `k9_agents/critic_actor/base_critic_actor_agent.py` | Actor-Critic refinement ABB — `generate` · `critique` · `refine` · `should_accept` · `finalize` |
| `k9_agents/critic_actor/k9_critic_actor_agent.py` | OOB LLM-driven Actor-Critic — override `critique()` to plug in a real external validator |

### Solutions Architect — BaseAgent vs K9ValidationLoopAgent

The generator, intake, and Claude Code scaffold all agents extending `BaseAgent` (one-shot) by default. The SA must decide at design time which agents need the validation loop.

**Decision rule — ask per agent:**
> *"Does this agent need to test something, observe the result, and decide whether to try again — or does it produce its answer in one pass?"*

| One-pass → `BaseAgent` | Iterative convergence → `K9ValidationLoopAgent` |
|---|---|
| Triage, routing, audit, guard, graph sync | Fraud signal correlation, claims evidence, compliance gap, document confidence |

When changing a generated agent to iterative: replace `class MyAgent(BaseAgent)` with `class MyAgent(K9ValidationLoopAgent)` and replace `execute()` with the five loop methods (`generate_hypothesis`, `run_validation`, `evaluate_observation`, `should_continue`, `finalize`). See Skill 10 in SKILLS.md.

### Factory pattern

All major components are provisioned through factories — never instantiated directly in application code:

- `LLMFactory.bootstrap(config)` then `LLMFactory.get(alias)` — returns cached `OllamaLLM`
- `ModelRouterFactory.get_router(config)` — returns cached `K9ModelRouter`
- `AgentRegistry.register(name, cls)` / `create(name)` — instantiates agents by name
- `OrchestratorRegistry` — same pattern for orchestrators

---

## Infrastructure (shared, always-on at <LAN_HOST_IP>)

| Service | Address |
|---|---|
| Ollama | `http://<LAN_HOST_IP>:11434` |
| PostgreSQL | `<LAN_HOST_IP>:5432` (databases: `k9aif` schema `k9aif`, EOC uses `eoc` schema `eoc`) |
| Kafka / Redpanda | `<LAN_HOST_IP>:9092` |
| Neo4j | `bolt://<LAN_HOST_IP>:7687` |
| Docling OCR | `http://<LAN_HOST_IP>:5001/v1/parse` |

`K9_ENV` environment variable controls governance enforcement: `development` / `test` permit NoopGovernance; `production` / `staging` cause `enforce_governance()` to raise.

### MCP (Model Context Protocol) layer

K9-AIF includes a full MCP client ABB stack for calling external tool servers:

| Component | Path | Role |
|---|---|---|
| `MCPHttpConnector` | `k9_core/integration/mcp_http_connector.py` | HTTP/HTTPS MCP client |
| `MCPStdioConnector` | `k9_core/integration/mcp_stdio_connector.py` | stdio MCP client |
| `BaseMCPAgent` | `k9_core/agent/base_mcp_agent.py` | Abstract base for MCP-aware agents |
| `MCPClientAgent` | `k9_agents/integration/mcp_client_agent.py` | Concrete MCP agent SBB |

The **Docling OCR MCP server** at `http://<LAN_HOST_IP>:5001/v1/parse` is the live tool server for document intelligence. It converts PDF, DOCX, and images to clean Markdown (tables, layout preserved), which agents consume as prompt context. `DocumentExtractorAgent` in the EOC connects to Docling via `MCPHttpConnector` — the connector type is config-driven, so any MCP-compatible tool server can be substituted without touching squad or orchestrator code.
