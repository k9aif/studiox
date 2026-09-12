# CLAUDE.md

Guidance for Claude Code in this repository. Full prior version (extended
config/persistence/MCP/adapter-table reference material) preserved in
`old-CLAUDE.md`. Step-by-step recipes live in `SKILLS.md` — **read it
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

Agents never call `OllamaLLM`/`LLMFactory` directly. Always:

```python
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
resp = llm_invoke(self.config, InferenceRequest(prompt=..., task_type=...))
```

`llm_invoke` raises `RuntimeError` on failure — it never silently returns
empty output; catch and handle explicitly. Full chain + adding a new
provider: `SKILLS.md` Skills 2 and 13.

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

## Everything is provisioned through factories

Never instantiate directly in application code: `LLMFactory`,
`ModelRouterFactory`, `AgentRegistry`, `OrchestratorRegistry`,
`SecretManagerFactory`, `CacheFactory`, `ObjectStorageFactory`. Every factory
`create(config)` has a zero-config default (env secrets, in-memory cache,
local storage) — no config key required for the common case. Adding a new
provider to any of these: `SKILLS.md` Skill 11.

## Kafka ownership

Only the **Router** (domain topics) and **Orchestrator** (results /
downstream topics) touch Kafka. Agents are constructed without a
`message_bus` — they share data sequentially through the Squad flow, not via
A2A messaging. `publish_event()` on an agent reaches the logger/monitor only.

## Pre-Push Checklist

- Every new `.py` file starts with the two-line header
  `# SPDX-License-Identifier: Apache-2.0` / `# K9-AIF Framework`, before any
  module docstring. Nearly universal in `k9_aif_abb/` but not enforced by
  any hook — check new files by hand; a whole adapter package (CrewAI) went
  missing it for a full release cycle before anyone noticed.
- No hardcoded IPs (`192.168.x.x` etc.) — env vars with localhost defaults:
  `"${POSTGRES_HOST:-localhost}"`, `"${OLLAMA_BASE_URL:-http://localhost:11434}"`
- No credentials in `config.yaml` — secrets in `.env` (gitignored) only
- `.env` never staged; `env-example` is the template
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

## Commands

```bash
# Setup
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Tests
pytest k9_aif_abb/tests/ -v                      # all
pytest k9_aif_abb/tests/test_framework.py -v     # framework stability only, no external services

# Run example apps (local)
./run_k9chat.sh
./run_acme_support_center.sh

# EOC (RHEL/Podman) — after git pull, always rebuild; restart alone won't pick up code
bash build.sh && bash run_eoc_pod.sh
sudo podman pod ps
sudo podman logs eoc-app-backend

# Generate a stub app
./k9_generator.sh preview <AppName>
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

## Where the rest lives

Config structure, persistence tables, MCP client stack, session management,
Zero Trust guard, the full Provider Adapter table, and detailed Squad/Agent
YAML examples were trimmed from this file per Anthropic's CLAUDE.md size
guidance (keep only what's needed nearly every session). They're either
self-evident from the source under `k9_aif_abb/`, covered step-by-step in
`SKILLS.md`, or preserved verbatim in `old-CLAUDE.md`.
