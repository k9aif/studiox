# K9X Studio

**From process to governed multi-agent code.**

K9X Studio turns the process you already have (a BPMN diagram, a process specification, an agent evaluation plan) into a governed [K9-AIF](https://github.com/k9aif/k9-aif-framework) architecture and a runnable scaffold. It maps every process step onto the Router → Orchestrator → Squad → Agent hierarchy, lets you review that mapping in a traceability matrix and reshape it on a visual canvas, then generates the project with k9x_Shield, Zero Trust and human-in-the-loop hooks already wired in.

Try it live: [studio.k9x.ai](https://studio.k9x.ai)

---

## Installation

```bash
pip install k9x
k9x studio
```

This opens a browser tab at `http://localhost:12999` (sign in with `demo` / `demo`). Useful flags:

```bash
k9x studio --port 8080          # use a different port
k9x studio --bg                 # run in the background, return immediately
k9x studio --stop               # stop a background instance
k9x config                      # write a starter .env with LLM provider settings
k9x upgrade                     # pip install --upgrade k9x
```

Run `k9x help` for the full command list.

---

## What you can import

| Input | Formats | What it drives |
|---|---|---|
| **BPMN diagram** | `.bpmn`, `.xml`, `.zip` from any BPMN 2.0 tool (Camunda, Bizagi, Blueworks Live, IBM Process Studio, …) | Lanes become Orchestrators and Squads, tasks become Agents or Adapters |
| **Process specification** | `.md`, `.txt`, `.html` spec or blueprint | Agents, tools, observability and behavioral rules; joins with the BPMN when both are staged |
| **Agent evaluation plan** | `.md` with Functional / Behavioral / Adversarial … eval sections | One `tests/evals/*.py` stub per test case, plus framework coverage on the **Evals** tab |

Any one input is enough; together they give the richest result.

**IBM Process Studio.** Process Studio's BPMN, blueprint and Agent Evaluation Plan exports work in the tiles above, including its GREEN / AMBER / RED autonomy-zone colouring. An Enterprise App Kit (`.zip`) import is shown in its own collapsible **IBM Process Studio** group on the Intake tab and is marked *coming soon*.

---

## Workflow

```
1. Intake          Upload BPMN / spec / eval plan → pre-checks → Granite Guardian screen → Generate
2. Traceability    Review and edit the Process → Implementation matrix → Confirm & Build Canvas
3. Canvas          Rearrange Routers, Orchestrators, Squads, Agents, Adapters
4. Generate        Generate Scaffold → download a ZIP, or browse it on the View Scaffold tab
```

The **Evals** and **Traceability** tabs are always present and stay empty until an input that feeds them is staged. You can also start from a template or compose the canvas by hand.

---

## Granite Guardian screening

Every file staged on the Intake tab is pre-checked and then screened by a Granite Guardian model before Studio uses it. Screening is **on by default**; turn it off in `.env`:

```bash
GUARDIAN_ENABLED=true                         # set to false to skip the Guardian screen
GOVERNANCE_LLM_ENDPOINT=http://127.0.0.1:11434
GOVERNANCE_LLM_MODEL=granite4.1-guardian:8b   # ollama pull granite4.1-guardian:8b
```

With screening on and no reachable Guardian model, uploads are blocked (the header shows **Guardian Offline**). With it off, the header shows **Guardian Off** and uploads skip the screen.

---

## LLM Configuration

An LLM is **optional**. Studio decides by where the canvas comes from:

| Canvas source | Uses the LLM? |
|---|---|
| Template (including **Regenerate** on a template canvas) | Never: always rebuilt from the original template |
| BPMN, structured blueprint, agent evaluation plan | Never: rule-based |
| Free-form spec with no agent register (`.md` / `.txt` / `.html`) | Yes, if configured; otherwise a generic starter template |
| Manual entry (no document) | Yes, if configured; otherwise a generic starter template |
| Narrated docs on Generate Scaffold | Only when an LLM is set on the Setup tab |

Scaffold code itself is always generated from templates, never by an LLM. Granite Guardian screening uses its own `GOVERNANCE_LLM_*` settings (see above).

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
| **Ollama** | `http://10.0.0.5:11434` | Local / self-hosted. No API key needed. |
| **OpenAI-compatible** | `https://api.openai.com/v1` | Also works with vLLM, LM Studio, Together AI |
| **Anthropic** | `https://api.anthropic.com` | Requires Anthropic API key |

> **Note:** `localhost` and `127.0.0.1` are intentionally blocked on the hosted instance at studio.k9x.ai to prevent the server's own resources from being used. Always use an IP address or hostname when configuring the endpoint.

### Recommended models

| Use case | Model |
|---|---|
| Local / fast | `qwen2.5:7b` |
| Local / quality | `qwen3.8:27b` (reasoning model; ~30 s per suggestion on a single GPU), `qwen2.5:32b` |
| OpenAI | `gpt-4o-mini` (best price/quality for JSON tasks) |
| Anthropic | `claude-haiku-4-5-20251001` (fast), `claude-sonnet-5` (quality) |

Avoid models under 7B: they rarely return valid architecture JSON, and Studio falls back to the starter template.

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
LLM_ENDPOINT=http://10.0.0.5:11434
LLM_MODEL=granite3-dense:2b
LLM_API_KEY=                        # leave blank for Ollama
```

The `.env` file is loaded automatically on startup and is excluded from source control.

#### 2. Environment variables (`--env-file` on `podman run`, used by `ubuntu/build-run.sh`)

`ubuntu/build-run.sh start` passes this project's own `.env` straight through via `--env-file` — see method 1 above; there's no separate `-e` flag list to maintain.

#### 3. `config.yaml` (file-based, alternative to `.env`)

Edit `config.yaml` in the studio root before starting:

```yaml
llm:
  enabled: true
  provider: ollama
  endpoint: "http://10.0.0.5:11434"
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

Or build and run the container (Podman required, no separately-published image — see `ubuntu/build-run.sh`):

```bash
./ubuntu/build-run.sh all
```

Open **http://localhost:8081**.

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
- Live demo: [studio.k9x.ai](https://studio.k9x.ai)
- Ecosystem: [k9x.ai/ecosystem](https://k9x.ai/ecosystem)
