# k9x_studio

**Visual Architecture Builder for K9-AIF Systems**

k9x_studio is a browser-based drag-and-drop IDE for designing K9-AIF multi-agent systems. It reads the `k9_aif_abb` component library, lets architects compose systems visually on a canvas, and generates production-ready YAML configuration and Python scaffold — the same output as `k9_generator.sh`, but designed rather than typed.

Try it live: [studio.k9x.ai](https://studio.k9x.ai)

---

## Workflow

```
1. Project Setup
   └── Name, author, domain, description

2. Canvas Design (drag-and-drop)
   ├── Palette (left): Router, Orchestrator, Squad, Agent, ...
   ├── Canvas (center): drop nodes, draw connections
   └── Inspector (right): configure selected node

3. Generate Architecture  (LLM-powered when configured)
   └── AI suggests Orchestrators, Squads, and Agents based on description

4. Export Scaffold
   └── Downloads ZIP: config/ + agents/ + squads/ + Python stubs
       OR writes directly to k9_projects/<AppName>/
```

---

## LLM Configuration

LLM is **optional but strongly recommended**. Without it the studio works in *demo mode* — templates and manual canvas composition are fully functional, but the **Generate Architecture** button produces a generic fallback instead of an AI-tailored suggestion.

### Why configure an LLM?

- **Generate Architecture** uses the LLM to suggest Orchestrators, Squads, and Agents suited to your project description
- **BPMN import** (complex diagrams) uses the LLM to intelligently group flat tasks into meaningful Squads

### Recommended approach — run LLM locally

Install [Ollama](https://ollama.ai) on your own machine or server and pull a model:

```bash
ollama pull granite3-dense:2b   # fast, good JSON output
# or
ollama pull llama3.1:8b         # higher quality suggestions
```

Then point the studio at your Ollama endpoint. Your data never leaves your environment.

### Supported providers

| Provider | Endpoint example | Notes |
|---|---|---|
| **Ollama** | `http://192.168.1.10:11434` | Local / self-hosted. No API key needed. |
| **OpenAI-compatible** | `https://api.openai.com/v1` | Also works with vLLM, LM Studio, Together AI |
| **Anthropic** | `https://api.anthropic.com` | Requires Anthropic API key |

> **Note:** `localhost` and `127.0.0.1` are intentionally blocked on the hosted instance at studio.k9x.ai to prevent the server's own resources from being used. Always use an IP address or hostname when configuring the endpoint.

### Recommended models

| Use case | Model |
|---|---|
| Local / fast | `granite3-dense:2b`, `mistral:7b` |
| Local / quality | `llama3.1:8b`, `llama3.2:3b` |
| OpenAI | `gpt-4o-mini` (best price/quality for JSON tasks) |
| Anthropic | `claude-haiku-4-5-20251001` (fast), `claude-sonnet-4-6` (quality) |

### Configuration methods

The studio checks LLM config in this priority order:

#### 1. `.env` file — recommended for self-hosted deployments

Copy `.env.sample` to `.env` and fill in your values:

```bash
cp .env.sample .env
```

```bash
# .env
LLM_PROVIDER=ollama
LLM_ENDPOINT=http://192.168.1.10:11434
LLM_MODEL=granite3-dense:2b
LLM_API_KEY=                        # leave blank for Ollama
```

The `.env` file is loaded automatically on startup and is excluded from source control.

#### 2. Environment variables (Docker / Podman `-e` flags)

```bash
podman run -d --name k9x_studio -p 8080:8080 \
  -e LLM_PROVIDER=ollama \
  -e LLM_ENDPOINT=http://192.168.1.10:11434 \
  -e LLM_MODEL=granite3-dense:2b \
  -e K9X_PROJECTS_ROOT="/k9x/projects" \
  -v ~/k9x-studio-working:/k9x/projects:Z \
  ghcr.io/k9aif/k9x-studio:latest
```

#### 3. `config.yaml` (file-based, alternative to `.env`)

Edit `config.yaml` in the studio root before starting:

```yaml
llm:
  enabled: true
  provider: ollama
  endpoint: "http://192.168.1.10:11434"
  model: granite3-dense:2b
  api_key: ""
```

#### 4. Browser UI (session-only, transient)

Click **⬡ LLM Config** at the bottom of the left panel. Enter endpoint, model, and optional API key. Config is held in your browser session only — it is **not stored** and clears on page refresh. Ideal for one-off use on a shared or public instance.

---

## Running locally

```bash
cd k9x_studio

# 1. Configure your environment (first time only)
cp .env.sample .env
# Edit .env — add your LLM endpoint, API keys, and any other external config

# 2. Start
./run.sh          # starts backend (port 8080) + frontend dev server (port 5173)
```

`.env` is gitignored and never committed. All secrets stay local to your machine.

Or pull and run the container:

```bash
podman pull ghcr.io/k9aif/k9x-studio:latest
podman run -d --name k9x_studio -p 8080:8080 \
  -e K9X_PROJECTS_ROOT="/k9x/projects" \
  -v ~/k9x-studio-working:/k9x/projects:Z \
  ghcr.io/k9aif/k9x-studio:latest
```

---

## Architecture

```
┌──────────┐    ┌────────────────────────────────────────────┐    ┌────────────────┐
│          │    │                  CANVAS                     │    │   INSPECTOR    │
│ PALETTE  │    │                                             │    │                │
│          │    │  [Router]────►[Orchestrator]                │    │ Node: Agent    │
│ Router   │    │                    │                        │    │ Name: FraudDet │
│ Orch.    │    │              [ClaimsSquad]                  │    │ Model: reason  │
│ Squad    │    │              ┌─────┴──────┐                 │    │ Pattern: loop  │
│ Agent    │    │          [Triage]  [Fraud] [Audit]          │    │ Role: ...      │
│ ValLoop  │    │                                             │    │                │
│ CritAct  │    │                                             │    │                │
│ Guard    │    │                                             │    │                │
└──────────┘    └────────────────────────────────────────────┘    └────────────────┘
```

---

## Component Palette → ABB Mapping

| Palette Node | K9-AIF ABB | Output |
|---|---|---|
| **Router** | `K9EventRouter` | `router/` Python + config |
| **Orchestrator** | `BaseOrchestrator` | `orchestrators/` Python + config |
| **Squad** | `BaseSquad` | `squads/yaml/<name>.yaml` |
| **Agent** | `BaseAgent` | `agents/yaml/<name>.yaml` + `agents/src/<name>.py` |
| **Validation Loop** | `K9ValidationLoopAgent` | Agent with iterative loop scaffold |
| **Critic-Actor** | `K9CriticActorAgent` | Agent with actor/critic scaffold |
| **Guard** | `BaseGovernance` | Governance config entry |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend canvas | React + [React Flow](https://reactflow.dev) |
| Frontend UI | TypeScript + CSS |
| Backend API | Python FastAPI |
| Scaffold generation | Jinja2 templates |
| Export | ZIP download or write to `k9_projects/` |

---

## References

- K9-AIF Framework: [github.com/k9aif/k9-aif-framework](https://github.com/k9aif/k9-aif-framework)
- Studio container: `ghcr.io/k9aif/k9x-studio:latest`
- Live demo: [studio.k9x.ai](https://studio.k9x.ai)
- Ecosystem: [k9x.ai/ecosystem](https://k9x.ai/ecosystem)
# studiox
