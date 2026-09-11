# CLAUDE.md

This file provides guidance to Claude Code when working with code in **this repository —
k9x_studio (studiox)**, the visual K9-AIF architecture builder. It is not the k9-aif-framework
repo; do not follow instructions here that assume a top-level `k9_aif_abb/`, `examples/`, or
`k9_projects/` — those belong to a different repo entirely.

## What this is

A browser-based drag-and-drop IDE for designing K9-AIF multi-agent systems: FastAPI backend +
React/Vite/React Flow frontend. Architects compose Router → Orchestrator → Squad → Agent on a
canvas, or import a spec doc (`.md`) or BPMN diagram (`.bpmn`), and generate production-ready
YAML + Python scaffold. Live at [studio.k9x.ai](https://studio.k9x.ai).

See `DESIGN.md` in the repo root for the self-agentization architecture (studiox's own backend is
itself built as a K9-AIF app — orchestrators/squads/agents under `orchestrators/`, `squads/yaml/`,
`studio_agents/`, not just procedural FastAPI routes).

## Dependency model — one thing to get right

studiox depends on the **framework via PyPI only** — `pip install -r requirements.txt` pulls
`k9-aif[s3]>=1.4.0` from PyPI. There is no vendored copy of the framework source in this repo.
If you ever see one reappear under `context/` or elsewhere, that's a regression — see the
`context/k9_aif_abb` removal (commit `906216f`) for why it was deleted. The one legitimate
exception: `generator/templates/*.j2` isn't shipped in the PyPI package, so the production
container build (`ubuntu/Containerfile`) copies those specifically from a local
`k9-aif-framework` checkout — nothing else.

## Commands

### Local dev setup

```bash
./run.sh
```
Uses a shared venv at `../../k9-aif-framework/.venv` (sibling repo under the same `ai/`
directory), installs `requirements.txt` into it, installs frontend deps if needed, and starts
both processes: backend (`uvicorn backend.main:app`) on `http://localhost:8090`, frontend
(`npm run dev`) on `http://localhost:5173`.

### Packaged install (what most users actually run)

```bash
pip install k9x
k9x studio            # opens http://localhost:12999
k9x studio --port 8080
k9x studio --bg / --stop
```

### Container build/run (production path — see `ubuntu/Containerfile`, `ubuntu/build-run.sh`)

```bash
./ubuntu/build-run.sh build   # podman build, context must be ai/ (parent of k9-aif-framework/)
./ubuntu/build-run.sh start   # runs on port 8081, needs .env in project root
```

### Tests

```bash
pytest backend/tests/ -v
```

**No `.claude/hooks` are configured in this repo** — if you're looking for the PostToolUse hook
table that used to be here, it described the framework repo, not this one, and has been removed.

## Architecture

### Backend layers

```
backend/api/routes.py          ← thin HTTP layer, validates input, calls into the router
  → studio_core/router/router_factory.route_event(event_type, payload)
    → orchestrators/*.py       ← e.g. SpecImportOrchestrator, BPMNImportOrchestrator
      → squads/yaml/*.yaml     ← e.g. spec_import_squad.yaml
        → studio_agents/       ← e.g. K9SubAgentSpawner-based parallel extraction
backend/services/*.py          ← private helper functions the agents call
  (spec_parsing_service.py, bpmn_service.py, scaffold_service.py, context_service.py)
```

Key endpoints (`backend/api/routes.py`): `POST /api/spec/import` (parse a `.md`/`.txt` spec doc,
return intake fields + canvas suggestion), `POST /api/bpmn/import` (parse a `.bpmn`, same output
shape), `GET /api/config`, `POST /api/setup/verify-framework`.

### Spec-doc import (`backend/services/spec_parsing_service.py`)

Parses a blueprint's **Agent Definition Register** (looks for a `### 3.1.8` or `### 3.3.1`
heading — check this against the actual document if import returns the generic fallback
suggestion instead of the real agent list; different blueprint generators use different section
numbering). Zone column (GREEN/AMBER/RED) drives `zone_to_agent_type()`: GREEN → adapter
(`BaseAgent`, no validation loop), AMBER → `K9ValidationLoopAgent`, RED → `K9CriticActorAgent`.

### BPMN import (`backend/services/bpmn_service.py`)

Lanes → one Orchestrator + one Squad each; tasks → Agents. **Does not currently read per-task
`color:background-color` zone coloring** that some BPMN sources embed (e.g. Process Studio
exports) — zone/agent-type assignment for BPMN-only import is a known gap, not yet wired the way
the spec-doc path is.

### Scaffold generation

Renders Jinja2 templates (`backend/templates/*.j2`) into a downloadable project scaffold —
`agents/src/*.py` (extending `k9_aif_abb.k9_core.agent.base_agent.BaseAgent` or
`k9_aif_abb.k9_agents.validation.K9ValidationLoopAgent`), `orchestrators/*.py`, `squads/yaml/*`,
`config/*`. **Known issue:** orchestrator-to-squad wiring has been found generating
mismatched pairs (an orchestrator loading a different lane's squad) — verify wiring in any
scaffold before treating it as correct; don't assume orchestrator N invokes squad N.

### Frontend

React + TypeScript + Vite + React Flow (XYFlow v12), Zustand store (`frontend/src/store.ts`),
canvas in `frontend/src/components/Canvas.tsx`. Node coloring is currently by **role**
(router/orchestrator/squad — fixed palette), not by autonomy zone.

## Related repos

- `k9-aif-framework` — the actual K9-AIF framework (ABBs), a sibling repo under the same `ai/`
  directory. Read its source directly for grounding on framework behavior; don't rely on a stale
  local copy.
- `studiox_v2` (`github.com/k9aif/studiox_v2`) — a separate fork, used for enhancement work that
  shouldn't touch this (studio.k9x.ai / IEEE-paper-referenced) repo directly. Don't assume changes
  there are reflected here or vice versa.
