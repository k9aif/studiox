# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework — CLI entry point
"""
k9aif — command line interface for K9-AIF framework.

Usage:
    k9aif verify
    k9aif version
    k9aif info
    k9aif --help
    k9aif --help develop
    k9aif --help faq
    k9aif --help patterns
    k9aif --help examples
    k9aif --help crewai
"""

from __future__ import annotations
import sys


# ── Help topics ──────────────────────────────────────────────────────────────

def _version_str() -> str:
    try:
        from importlib.metadata import version as pkg_version
        try:
            return pkg_version("k9-aif")
        except Exception:
            return pkg_version("k9_aif_abb")
    except Exception:
        return "unknown"


HELP_MAIN = """
k9aif — K9-AIF Framework CLI  v{version}
Architecture-First Framework for Governed, Modular Agentic AI Systems
Author:    Ravi Natarajan — https://k9x.ai
Community: https://discord.gg/TbyFPvKJ5

COMMANDS:
  k9aif verify              Smoke test — confirms framework is installed correctly
  k9aif version             Show installed version
  k9aif info                Show framework components and links

HELP TOPICS:
  k9aif --help              This help message
  k9aif --help develop      How to build agents, squads, and orchestrators
  k9aif --help faq          Frequently asked questions
  k9aif --help patterns     Architectural patterns in K9-AIF
  k9aif --help examples     Available reference implementations
  k9aif --help crewai       Using K9-AIF with CrewAI

QUICK START:
  k9aif init
  python main.py

UPGRADE:
  pip install --upgrade k9-aif

LINKS:
  Framework:  https://github.com/k9aif/k9-aif-framework
  Docs:       https://k9x.ai
  Blog:       https://blog.k9x.ai
  Graph:      https://graph.k9x.ai
"""

HELP_DEVELOP = """
k9aif --help develop
─────────────────────────────────────────────────────
DEVELOPMENT GUIDE — Building with K9-AIF

EXECUTION HIERARCHY:
  Event → Router → Orchestrator → Squad → Agent → LLM

STEP 1 — Create an Agent (extends BaseAgent)
  from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

  class MyAgent(BaseAgent):
      layer = "MyAgent SBB"
      def execute(self, payload: dict) -> dict:
          # call LLM via router
          from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
          from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
          req = InferenceRequest(prompt="...", task_type="reasoning")
          resp = llm_invoke(self.config, req)
          return {"output": resp.output}

STEP 2 — Create a Squad (YAML driven)
  squads:
    MySquad:
      agents: [AgentOne, AgentTwo]
      flow:
        - agent: AgentOne
          result_key: step_one
        - agent: AgentTwo
          result_key: step_two

STEP 3 — Create an Orchestrator (extends BaseOrchestrator)
  from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator

  class MyOrchestrator(BaseOrchestrator):
      layer = "MyOrchestrator SBB"
      def execute_flow(self, payload: dict) -> dict:
          squad = self._load_squad("MySquad")
          return squad.run(payload)

STEP 4 — Create a Router (extends BaseRouter)
  from k9_aif_abb.k9_core.router.base_router import BaseRouter

  class MyRouter(BaseRouter):
      layer = "MyRouter SBB"
      def route(self, payload: dict) -> dict:
          orchestrator = MyOrchestrator(config=self.config)
          return orchestrator.execute_flow(payload)

GOVERNANCE:
  Set K9_ENV=development  → NoopGovernance (warning only)
  Set K9_ENV=production   → GovernanceError raised if no policy configured

FULL REFERENCE:
  See CLAUDE.md and SKILLS.md in the framework repository.
"""

HELP_FAQ = """
k9aif --help faq
─────────────────────────────────────────────────────
FREQUENTLY ASKED QUESTIONS

Q: What is K9-AIF?
A: An open-source, architecture-first framework for building governed
   multi-agent AI systems. It applies GoF, POSA, and TOGAF patterns
   to agentic AI — the same discipline that produced Eclipse and VS Code.

Q: What is the difference between ABB and SBB?
A: ABB (Architecture Building Block) = abstract contract. Never modified.
   SBB (Solution Building Block) = your concrete implementation.
   You extend ABBs. You never modify them.

Q: Does K9-AIF replace LangChain or CrewAI?
A: No. K9-AIF is the governance and architecture layer above them.
   CrewAI agents can use K9-AIF's model router transparently via
   K9XLiteLLMBridgeAdapter. Run: k9aif --help crewai

Q: Which LLM providers are supported?
A: Ollama (default), IBM Watsonx, any OpenAI-compatible endpoint.
   Provider switching is a config change — no code change needed.

Q: How do I add governance to my agents?
A: Call self.enforce_governance() at the top of execute().
   In production (K9_ENV=production), agents without a governance
   policy will raise PermissionError.

Q: How do I persist routing decisions?
A: K9ModelRouter automatically persists every routing decision
   to SQLite (default) or PostgreSQL. No extra code needed.

Q: Where is the flagship reference implementation?
A: examples/K9X_Enterprise_Insurance_OperationsCenter/ — a full
   production system: Kafka, PostgreSQL, Podman, 3 containers.

Q: How do I scaffold a new project?
A: Use k9_generator.sh in the framework repository:
   ./k9_generator.sh run MyApp
"""

HELP_PATTERNS = """
k9aif --help patterns
─────────────────────────────────────────────────────
ARCHITECTURAL PATTERNS IN K9-AIF

GoF PATTERNS (structurally present — not decorative):

  Factory         LLMFactory, ModelRouterFactory, AgentRegistry
                  → provisions components; never instantiate directly

  Strategy        BaseModelRouter / K9ModelRouter
                  → pluggable model routing logic

  Template Method BaseAgent.execute(), BaseValidationLoopAgent loop
                  → fixed skeleton, override specific steps

  Adapter         K9CrewAIAdapter, K9XLiteLLMBridgeAdapter
                  → bridges external frameworks to K9-AIF contracts

  Chain of Resp.  GovernancePipeline
                  → pre_process → agent → post_process

  Observer        publish_event() on every agent and orchestrator
                  → audit trail, monitoring, Kafka events

POSA PATTERNS:

  Layers          Router → Orchestrator → Squad → Agent
                  → each layer knows only what is below it

  Reactor         K9EventRouter — event-driven dispatch

TOGAF:
  ABB/SBB         Abstract contracts + concrete implementations
                  → same decision as Eclipse extension points

FULL CATALOG:
  https://github.com/k9aif/k9aif-patterns
"""

HELP_EXAMPLES = """
k9aif --help examples
─────────────────────────────────────────────────────
REFERENCE IMPLEMENTATIONS

All examples are in: examples/ in the framework repository.

ACME Support Center (starter)
  examples/acme_support_center/
  → Router + 1 Orchestrator + 1 Squad + 3 Agents
  → Run: ./run_acme_support_center.sh

K9Chat (conversational)
  examples/k9chat/
  → Multi-turn chat with model routing
  → Run: ./run_k9chat.sh

Enterprise Operations Center — EOC (flagship)
  examples/K9X_Enterprise_Insurance_OperationsCenter/
  → 3 containers (Router, Orchestrator, FastAPI backend)
  → Kafka messaging, PostgreSQL, Podman deployment
  → Every K9-AIF pattern in production
  → Run: bash run_eoc_pod.sh

Zero Trust Demo
  examples/zero_trust_execution_demo/
  → Governance enforcement in action

DoDAF 2.0 Pipeline (external)
  github.com/k9aif/dow
  → 49 CrewAI agents + K9-AIF governance layer
  → Full DoDAF 6-stage + JCIDS pipeline
"""

HELP_CREWAI = """
k9aif --help crewai
─────────────────────────────────────────────────────
USING K9-AIF WITH CREWAI

K9-AIF is not a replacement for CrewAI.
K9-AIF is the governance and model routing layer above CrewAI.

INSTALL:
  pip install k9-aif
  pip install "k9-aif[crewai]"    # installs K9-AIF + CrewAI together
  pip install crewai>=1.14        # or install CrewAI separately

WIRE K9-AIF MODEL ROUTER INTO CREWAI AGENTS:
  from k9_aif_abb.k9_adapters.crewai.k9x_litellm_bridge_adapter import K9XLiteLLMBridgeAdapter

  llm = K9XLiteLLMBridgeAdapter(
      k9_config=config,        # your K9-AIF config.yaml
      task_type="reasoning",   # drives K9ModelRouter scoring
      agent_name="MyAgent",    # for audit trail
  )

  agent = Agent(role="...", goal="...", llm=llm)

Now every LLM call from this CrewAI agent routes through K9ModelRouter:
  → weighted scoring (task_type, cost, latency, sensitivity)
  → routing decision persisted to state store
  → full audit trail

WRAP A FULL CREW IN K9-AIF:
  from k9_aif_abb.k9_adapters.crewai.k9_crewai_adapter import K9CrewAIAdapter

  adapter = K9CrewAIAdapter(crew)
  result = adapter.execute(payload)   # K9-AIF payload in, K9-AIF result out

WHAT CHANGES:    CrewAI agents route through K9ModelRouter
WHAT STAYS:      All CrewAI agent YAMLs, task definitions, crew structure

VERIFIED:  CrewAI 1.14.6
"""

# ── Commands ─────────────────────────────────────────────────────────────────

def verify():
    """Run a framework smoke test — no LLM needed."""
    print("K9-AIF Framework — Smoke Test")
    print("=" * 40)

    passed = 0
    failed = 0

    def check(label, fn):
        nonlocal passed, failed
        try:
            fn()
            print(f"  ✓  {label}")
            passed += 1
        except Exception as exc:
            print(f"  ✗  {label}: {exc}")
            failed += 1

    check("BaseAgent import", lambda: __import__(
        "k9_aif_abb.k9_core.agent.base_agent", fromlist=["BaseAgent"]))
    check("BaseRouter import", lambda: __import__(
        "k9_aif_abb.k9_core.router.base_router", fromlist=["BaseRouter"]))
    check("BaseOrchestrator import", lambda: __import__(
        "k9_aif_abb.k9_core.orchestration.base_orchestrator", fromlist=["BaseOrchestrator"]))
    check("BaseSquad import", lambda: __import__(
        "k9_aif_abb.k9_squad.base_squad", fromlist=["BaseSquad"]))
    check("LLMFactory import", lambda: __import__(
        "k9_aif_abb.k9_factories.llm_factory", fromlist=["LLMFactory"]))
    check("ModelRouterFactory import", lambda: __import__(
        "k9_aif_abb.k9_factories.model_router_factory", fromlist=["ModelRouterFactory"]))
    check("AgentRegistry import", lambda: __import__(
        "k9_aif_abb.k9_agents.registry.agent_registry", fromlist=["AgentRegistry"]))
    check("Governance pipeline import", lambda: __import__(
        "k9_aif_abb.k9_core.governance.pipeline", fromlist=["require_governance"]))
    check("InferenceRequest import", lambda: __import__(
        "k9_aif_abb.k9_inference.models.inference_request", fromlist=["InferenceRequest"]))
    check("K9CrewAIAdapter import", lambda: __import__(
        "k9_aif_abb.k9_adapters.crewai.k9_crewai_adapter", fromlist=["K9CrewAIAdapter"]))
    check("BaseValidationLoopAgent import", lambda: __import__(
        "k9_aif_abb.k9_agents.validation", fromlist=["BaseValidationLoopAgent"]))

    def _test_governance():
        from k9_aif_abb.k9_core.governance.pipeline import require_governance, NoopGovernance
        gov = require_governance(None, "development")
        assert isinstance(gov, NoopGovernance)
    check("Governance enforcement (dev mode)", _test_governance)

    def _test_registry():
        from k9_aif_abb.k9_agents.registry.agent_registry import AgentRegistry
        from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

        class _TestAgent(BaseAgent):
            layer = "TestAgent"
            def execute(self, payload):
                return {"ok": True}

        registry = AgentRegistry()
        registry.register("_TestAgent", _TestAgent)
        agent = registry.create("_TestAgent")
        result = agent.execute({})
        assert result["ok"] is True
    check("Agent registry — register + create + execute", _test_registry)

    print()
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print()
        print("K9-AIF is installed correctly and ready to use.")
        print("Run 'k9aif --help develop' to start building.")
    else:
        print()
        print("Some checks failed. Ensure Python 3.11+ and retry.")
        sys.exit(1)


def version():
    try:
        from importlib.metadata import version as pkg_version
        try:
            v = pkg_version("k9-aif")
        except Exception:
            v = pkg_version("k9_aif_abb")
        print(f"k9-aif {v}")
    except Exception:
        print("k9-aif (version unknown)")


def info():
    print("K9-AIF Framework")
    print("Architecture-First Framework for Governed, Modular Agentic AI Systems")
    print()
    print("  Framework:  https://github.com/k9aif/k9-aif-framework")
    print("  Docs:       https://k9x.ai")
    print("  Blog:       https://blog.k9x.ai")
    print("  Graph:      https://graph.k9x.ai")
    print()
    print("  License:    Apache 2.0")
    print("  Author:     Ravi Natarajan, AI Systems Architect, IBM")
    print()
    print("Key ABBs:")
    print("  BaseAgent          BaseRouter         BaseOrchestrator")
    print("  BaseSquad          BaseModelRouter    BaseGovernance")
    print("  BaseValidationLoopAgent               BaseCriticActorAgent")
    print("  BaseSecretManager  BaseCache          K9CrewAIAdapter")
    print()
    print("Run 'k9aif --help' for all commands.")


GENERATE_TEMPLATES = {
    "hello-world": '''# K9-AIF Hello World Agent
# Save as test.py and run: python test.py
# Requires: config.yaml (run 'k9aif init' first) + Ollama running

import yaml
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke


class HelloWorldAgent(BaseAgent):
    layer = "HelloWorldAgent SBB"

    def execute(self, payload: dict) -> dict:
        req = InferenceRequest(
            prompt=f"Say hello to {payload.get('name', 'World')} in one sentence.",
            task_type="general",
        )
        resp = llm_invoke(self.config, req)
        return {"agent": "HelloWorldAgent", "output": resp.output, "model": resp.model_alias}


if __name__ == "__main__":
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    agent = HelloWorldAgent(config=config)
    result = agent.execute({"name": "K9-AIF"})
    print(f"Output : {result['output']}")
    print(f"Model  : {result['model']}")
''',

    "agent": '''# K9-AIF Agent Template
# Rename class and implement execute()

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
from typing import Any, Dict, Optional


class MyAgent(BaseAgent):
    layer = "MyAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = InferenceRequest(
            prompt=f"Your prompt here. Input: {payload}",
            task_type="reasoning",   # general | reasoning | extraction | summarization
        )
        resp = llm_invoke(self.config, req)
        self.publish_event({"type": "MyAgentCompleted", "job_id": payload.get("job_id")})
        return {"agent": "MyAgent", "output": resp.output, "model": resp.model_alias}
''',

    "router": '''# K9-AIF Router Template
from k9_aif_abb.k9_core.router.base_router import BaseRouter
from typing import Any, Dict, Optional


class MyRouter(BaseRouter):
    layer = "MyRouter SBB"

    def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_type = payload.get("event_type", "")
        self.publish_event({"type": "Routed", "event_type": event_type})
        # Return orchestrator result
        from my_orchestrator import MyOrchestrator
        return MyOrchestrator(config=self.config).execute_flow(payload)
''',
}


COMPLETE_FILES = {
    "config/config.yaml": """\
# K9-AIF config.yaml — uses mock LLM (no Ollama needed)
inference:
  router:
    type: k9_model_router
    default_model: general
    persistence:
      enabled: true
      provider: sqlite
      sqlite:
        db_path: "./runtime/k9_model_router.db"

  llm_factory:
    base_url: "http://localhost:11434"
    provider: mock
    models:
      general: "general"
      reasoning: "reasoning"

  models:
    general:
      provider: mock
      llm_ref: general
      capabilities: [general, chat, summarization]
    reasoning:
      provider: mock
      llm_ref: reasoning
      capabilities: [reasoning, analysis]
""",

    "squads/my_squad.yaml": """\
squads:
  MySquad:
    description: "A simple K9-AIF squad with one agent."
    agents:
      - MyAgent
    flow:
      - agent: MyAgent
        result_key: my_agent_output
""",

    "agents/src/my_agent.py": '''\
# agents/src/my_agent.py — K9-AIF Agent SBB
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
from typing import Any, Dict, Optional


class MyAgent(BaseAgent):
    layer = "MyAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = InferenceRequest(
            prompt=f"Process this input: {payload.get('input', '')}",
            task_type="general",
        )
        resp = llm_invoke(self.config, req)
        self.publish_event({"type": "MyAgentCompleted"})
        return {"agent": "MyAgent", "output": resp.output, "model": resp.model_alias}
''',

    "orchestrators/my_orchestrator.py": '''\
# orchestrators/my_orchestrator.py — K9-AIF Orchestrator SBB
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator
from k9_aif_abb.k9_squad.squad_loader import SquadLoader
from k9_aif_abb.k9_agents.registry.agent_registry import AgentRegistry
from typing import Any, Dict

from agents.src.my_agent import MyAgent


class MyOrchestrator(BaseOrchestrator):
    layer = "MyOrchestrator SBB"

    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        registry = AgentRegistry()
        registry.register("MyAgent", lambda: MyAgent(config=self.config))

        loader = SquadLoader(registry)
        squad_path = str(Path(__file__).resolve().parents[1] / "squads" / "my_squad.yaml")
        squad = loader.load_one(squad_path, "MySquad")

        self.publish_status("started", {"job_id": payload.get("job_id", "")})
        result = squad.run(payload)
        self.publish_status("completed", {"job_id": payload.get("job_id", "")})
        return result
''',

    "router/my_router.py": '''\
# router/my_router.py — K9-AIF Router SBB
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from k9_aif_abb.k9_core.router.base_router import BaseRouter
from typing import Any, Dict

from orchestrators.my_orchestrator import MyOrchestrator


class MyRouter(BaseRouter):
    layer = "MyRouter SBB"

    def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("[MyRouter] Routing event: %s", payload.get("job_id", ""))
        orchestrator = MyOrchestrator(config=self.config)
        return orchestrator.execute_flow(payload)
''',

    "main.py": '''\
# main.py — entry point: Router → Orchestrator → Squad → Agent
import sys, yaml
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

# Check for .env before anything else
env_file = Path(__file__).parent / ".env"
if not env_file.exists():
    print()
    print("  ⚠  .env not found.")
    print()
    print("     Copy env-example to get started:")
    print("       cp env-example .env")
    print()
    print("     Then run again: python main.py")
    print()
    raise SystemExit(1)

load_dotenv(env_file)

from router.my_router import MyRouter

if __name__ == "__main__":
    config_path = Path(__file__).parent / "config" / "config.yaml"
    if not config_path.exists():
        print("  ⚠  config/config.yaml not found.")
        raise SystemExit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    print()
    print("  K9-AIF — Router → Orchestrator → Squad → Agent")
    print("  " + "─" * 48)
    print()

    router = MyRouter(config=config)
    result = router.route({"input": "Hello from K9-AIF", "job_id": "demo-001"})

    print(f"  Result : {result}")
    print()
    print("  Pipeline completed successfully.")
    print()
''',
    "env-example": """\
# K9-AIF Environment Variables
# Copy this file to .env and fill in your values:
#   cp env-example .env

# Runtime environment — controls governance enforcement
# development | test | staging | production
K9_ENV=development

# Ollama LLM server — uncomment when switching from mock to real LLM
# OLLAMA_BASE_URL=http://localhost:11434

# OpenAI (optional — if using OpenAI provider)
# OPENAI_API_KEY=sk-...

# Anthropic (optional — if using Anthropic provider)
# ANTHROPIC_API_KEY=sk-ant-...

# IBM watsonx (optional)
# WATSONX_API_KEY=
# WATSONX_PROJECT_ID=
# WATSONX_URL=https://us-south.ml.cloud.ibm.com

# PostgreSQL (optional — defaults to SQLite)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=k9aif
# POSTGRES_USER=k9aif
# POSTGRES_PASSWORD=

# Kafka / Redpanda (optional — for event-driven squads)
# KAFKA_BOOTSTRAP_SERVERS=localhost:9092
""",
    ".gitignore": """\
__pycache__/
*.pyc
*.pyo
.DS_Store
.env
runtime/
*.db
*.log
.venv/
venv/
dist/
build/
*.egg-info/
""",
}


K9AIF_CONTEXT_MD = """\
# K9-AIF Context — Architecture-First Agentic AI Framework

K9-AIF is a Python framework for designing and building governed, modular multi-agent AI systems.
Every solution is decomposed from business requirements into Architecture Building Blocks (ABBs)
and Solution Building Blocks (SBBs), then assembled into Squads that execute as event-driven pipelines.

## Core Concepts

**ABB (Architecture Building Block)** — Abstract contracts in `k9_aif_abb/`. Define interfaces,
lifecycle, and governance hooks. Never contain domain logic.

**SBB (Solution Building Block)** — Concrete implementations that extend ABBs with domain-specific
behavior. Live in your project folder (e.g. `agents/src/`, `orchestrators/`, `router/`).

## Execution Hierarchy

```
Event → Router
    └── Orchestrator
            └── Squad
                    └── Agent → LLM
```

- **Router** — single entry point. Routes events by `event_type` to the correct Orchestrator.
- **Orchestrator** — coordinates a Squad for a domain workflow.
- **Squad** — executes a defined flow of Agents in sequence. Each Agent enriches shared context progressively.
- **Agent** — implements `execute(payload) -> dict`. Calls LLM via `llm_invoke`.

## Three-Layer Decoupling — Never Violate

| Layer | Knows about | Does NOT know |
|---|---|---|
| Router | Orchestrators only | Squads, Agents |
| Orchestrator | Its Squad only | Routers, other Orchestrators |
| Squad | Its Agents only | Orchestrators |
| Agent | Its own behavior | Squads, routing, next Agent |

## Add a New Agent

**1. Agent YAML** — `agents/yaml/my_agent.yaml`
```yaml
name: MyAgent
class: MyAgent
description: What this agent does.
pattern: reasoning
model: reasoning
role: You are a ...
goal: Your goal is to ...
instructions:
  - Instruction one
output_schema:
  result: string
  confidence: float
governance:
  pre_process: true
  post_process: false
```

**2. Agent Python** — `agents/src/my_agent.py`
```python
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke

class MyAgent(BaseAgent):
    layer = "MyAgent SBB"

    def execute(self, payload):
        prompt = f"Role: {self.config.get('role')}\\nInput: {payload}"
        req = InferenceRequest(prompt=prompt, task_type=self.config.get("model", "general"))
        resp = llm_invoke(self.config, req)
        self.publish_event({"type": "MyAgentCompleted"})
        return {"agent": "MyAgent", "output": resp.output.strip(), "model_used": resp.model_alias}
```

**3. Register in `_load_squad()`** and **add to squad YAML flow**.

## Add a New Squad — `squads/my_squad.yaml`

```yaml
squads:
  MySquad:
    description: What this squad does.
    agents:
      - AgentOne
      - AgentTwo
    flow:
      - agent: AgentOne
        result_key: agent_one
      - agent: AgentTwo
        result_key: agent_two
```

Flow steps MUST be dicts with an `agent:` key — plain strings raise `ValueError`.

## LLM Invocation — Always Use This Pattern

```python
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke

req = InferenceRequest(
    prompt="Your prompt",
    task_type="reasoning",       # drives model scoring
    sensitivity="confidential",  # optional
    latency_budget="realtime",   # optional
    cost_profile="minimal",      # optional
)
resp = llm_invoke(self.config, req)
# resp.output, resp.model_alias, resp.provider, resp.latency_ms
```

Never call `OllamaLLM` or `LLMFactory` directly from agent code.

## Config Structure — `config/config.yaml`

```yaml
inference:
  router:
    type: k9_model_router
    default_model: general
    persistence:
      enabled: true
      provider: sqlite
  llm_factory:
    base_url: "http://localhost:11434"
    models:
      general: "llama3.2:1b"
      reasoning: "granite3-dense:2b"
  models:
    general:
      provider: ollama
      llm_ref: general
      capabilities: [general, chat, summarization]
    reasoning:
      provider: ollama
      llm_ref: reasoning
      capabilities: [reasoning, analysis, extraction]
```

## Iterative Agents — Use `K9ValidationLoopAgent`

When an agent must test a hypothesis, observe a result, and decide whether to retry:

```python
from k9_aif_abb.k9_agents.validation import K9ValidationLoopAgent, ValidationDisposition

class FraudValidationAgent(K9ValidationLoopAgent):
    def generate_hypothesis(self, loop_ctx): ...
    def run_validation(self, hypothesis, loop_ctx): ...
    def evaluate_observation(self, tool_result, loop_ctx): ...
    def should_continue(self, observation, loop_ctx):
        if observation["confidence"] >= 0.9:
            return ValidationDisposition.FINALIZE
        return ValidationDisposition.CONTINUE
    def finalize(self, loop_ctx): ...
```

One-pass → extend `BaseAgent`. Iterative convergence → extend `K9ValidationLoopAgent`.

## Governance

`K9_ENV=development` — NoopGovernance logs WARNING, continues.
`K9_ENV=production` — `enforce_governance()` raises `PermissionError`.

```python
def execute(self, payload):
    self.enforce_governance()   # raises in production if not configured
    ...
```

## Key CLI Commands

```bash
k9aif verify                   # smoke test
k9aif --generate complete      # scaffold full project
k9aif --context-init           # write k9aif_context.md to current folder
k9aif list agents              # list framework components
k9aif doctor                   # check environment
```

## Links

- Framework: https://github.com/k9aif/k9-aif-framework
- Docs: https://k9x.ai
- Blog: https://blog.k9x.ai
"""

K9AIF_README_MD = """\
# My K9-AIF Project

Built with [K9-AIF](https://k9x.ai) — Architecture-First Framework for Governed, Modular Agentic AI Systems.

## Quick Start

```bash
pip install k9-aif
k9aif --generate complete
cp env-example .env        # copy and edit your environment variables
python main.py
```

## Environment Setup

```bash
cp env-example .env
```

Open `.env` and set your values. The starter project uses a mock LLM — no API keys needed to run for the first time. When you are ready to connect a real LLM, uncomment and set `OLLAMA_BASE_URL` (or your provider's key) in `.env`.

> `.env` is in `.gitignore` — never commit it.

## Project Structure

```
config/config.yaml           ← LLM + inference config
agents/src/my_agent.py       ← Agent SBB (extend BaseAgent)
agents/yaml/                 ← Agent YAML definitions
orchestrators/               ← Orchestrator SBB
router/                      ← Router SBB
squads/                      ← Squad YAML flow definitions
runtime/                     ← Routing state store (auto-created)
main.py                      ← Entry point
```

## AI Coding Assistant Setup

This project includes `k9aif_context.md` — a complete description of K9-AIF architecture,
patterns, and development recipes. Point your AI assistant at it:

**Claude Code** — add to your `CLAUDE.md`:
```
@k9aif_context.md
```

**GitHub Copilot** — add contents to `.github/copilot-instructions.md`

**Cursor / Windsurf** — add contents to `.cursorrules`

**IBM BoB or any LLM chat** — start your session with:
> "Read k9aif_context.md first, then help me build on K9-AIF."

## Learn More

- Docs: https://k9x.ai
- Blog: https://blog.k9x.ai
- Framework: https://github.com/k9aif/k9-aif-framework
"""


def context_init(silent=False):
    """Write k9aif_context.md, README.md, and wire CLAUDE.md for Claude Code."""
    import time
    from pathlib import Path

    if not silent:
        print()
        print("  K9-AIF — Context Init")
        print("  " + "─" * 40)
        print()

    def _write(filename, content, label=None):
        label = label or filename
        if not silent:
            print(f"  Writing {label:<30}", end="", flush=True)
            time.sleep(0.15)
        path = Path.cwd() / filename
        if path.exists():
            if not silent:
                print("  ○  (exists — skipped)")
        else:
            path.write_text(content)
            if not silent:
                print("  ✓")

    _write("k9aif_context.md", K9AIF_CONTEXT_MD)
    _write("README.md", K9AIF_README_MD)

    # Wire Claude Code — write or append @k9aif_context.md to CLAUDE.md
    claude_md = Path.cwd() / "CLAUDE.md"
    import_line = "@k9aif_context.md"
    if not silent:
        print(f"  Wiring CLAUDE.md                ", end="", flush=True)
        time.sleep(0.15)
    if claude_md.exists():
        existing = claude_md.read_text()
        if import_line not in existing:
            claude_md.write_text(existing.rstrip() + f"\n\n{import_line}\n")
            if not silent:
                print("  ✓  (appended @k9aif_context.md)")
        else:
            if not silent:
                print("  ○  (already wired)")
    else:
        claude_md.write_text(f"{import_line}\n")
        if not silent:
            print("  ✓")

    if not silent:
        print()
        print("  Claude Code: reads k9aif_context.md automatically via CLAUDE.md")
        print("  Other tools: see README.md for setup instructions")
        print()


def generate_complete():
    """Generate a complete K9-AIF project with proper folder structure."""
    import time
    from pathlib import Path

    print()
    print("  K9-AIF — Architecture-First Agentic AI Framework")
    print("  " + "─" * 48)
    print()

    steps = [
        ("config",        ["config"]),
        ("agents",        ["agents/src"]),
        ("orchestrators", ["orchestrators"]),
        ("router",        ["router"]),
        ("squads",        ["squads"]),
        ("runtime",       ["runtime"]),
    ]

    for label, dirs in steps:
        print(f"  Scaffolding {label} ...", end="", flush=True)
        time.sleep(0.15)
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)
        print("  ✓")

    print()

    file_labels = {
        "config/config.yaml":               "Generating config               ",
        "agents/src/my_agent.py":           "Generating agent                ",
        "orchestrators/my_orchestrator.py": "Generating orchestrator         ",
        "router/my_router.py":              "Generating router               ",
        "squads/my_squad.yaml":             "Generating squad                ",
        "main.py":                          "Generating main                 ",
        "env-example":                      "Generating env-example          ",
        ".gitignore":                       "Generating .gitignore           ",
    }

    for filepath, content in COMPLETE_FILES.items():
        label = file_labels.get(filepath, f"Generating {filepath:<30}")
        print(f"  {label}", end="", flush=True)
        time.sleep(0.2)
        path = Path.cwd() / filepath
        if path.exists():
            print("  ○  (exists — skipped)")
        else:
            path.write_text(content)
            print("  ✓")

    context_init(silent=True)

    print()
    print("  " + "─" * 48)
    print()
    print("  Done!")
    print()
    print("  Ready to rumble!")
    print()
    print("  Next: python main.py")
    print()
    print("> ", end="", flush=True)
    print()


def generate_n8n_hello_world():
    from pathlib import Path

    print()
    print("K9-AIF — Generate n8n Hello World Example")
    print("==========================================")
    print()

    app_name = input("App name [n8n_helloworld]: ").strip() or "n8n_helloworld"
    port = input("Port [8001]: ").strip() or "8001"

    base = Path.cwd() / app_name
    if base.exists():
        print(f"\n  ✗  Folder '{app_name}' already exists. Remove it or choose a different name.")
        return

    # Create folder structure
    (base / "agents" / "src").mkdir(parents=True)
    (base / "agents" / "yaml").mkdir(parents=True)
    (base / "orchestrators").mkdir(parents=True)
    (base / "config").mkdir(parents=True)
    (base / "api").mkdir(parents=True)

    # __init__.py files
    for d in [base, base/"agents", base/"agents"/"src", base/"orchestrators", base/"api"]:
        (d / "__init__.py").write_text("")

    # .gitignore
    (base / ".gitignore").write_text("__pycache__/\n*.pyc\n*.pyo\n.DS_Store\n.env\n")

    # agents/yaml/hello_world_agent.yaml
    (base / "agents" / "yaml" / "hello_world_agent.yaml").write_text(
        f"""name: HelloWorldAgent
class: HelloWorldAgent

description: >
  Minimal demonstration agent. Accepts any payload and returns
  a greeting. No LLM call required — pure pipeline demo.

pattern: reasoning
model: general

role: >
  You are a friendly K9-AIF demonstration agent.

goal: >
  Return a Hello World greeting to confirm the K9-AIF pipeline is working.

instructions:
  - Return a greeting message confirming the pipeline is operational
  - Echo back the caller name if provided in the payload

output_schema:
  message: string
  caller: string
  agent: string
  status: string

governance:
  pre_process: false
  post_process: false
"""
    )

    # agents/src/hello_world_agent.py
    (base / "agents" / "src" / "hello_world_agent.py").write_text(
        """# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from typing import Any, Dict, Optional
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class HelloWorldAgent(BaseAgent):

    layer = "HelloWorldAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        caller = payload.get("caller", "n8n")
        self.logger.info("[%s] Received payload from: %s", self.layer, caller)
        self.publish_event({"type": "HelloWorldCompleted", "agent": "HelloWorldAgent"})
        return {
            "message": f"Hello World from K9-AIF Agent! Triggered by: {caller}",
            "caller": caller,
            "agent": "HelloWorldAgent",
            "status": "success",
            "pipeline": "Orchestrator \\u2192 Squad \\u2192 Agent",
        }
"""
    )

    # orchestrators/hello_world_orchestrator.py
    (base / "orchestrators" / "hello_world_orchestrator.py").write_text(
        """# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from typing import Any, Dict, Optional
import logging
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator

log = logging.getLogger(__name__)


class HelloWorldOrchestrator(BaseOrchestrator):

    layer = "HelloWorldOrchestrator SBB"

    def __init__(self, squad, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)
        self.squad = squad

    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        log.info("[%s] Running squad for event: %s", self.layer, payload)
        result = self.squad.run(dict(payload))
        self.publish_status("completed", {"type": "HelloWorldFlowCompleted"})
        return result

    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute_flow(event)
"""
    )

    # config/squads.yaml
    (base / "config" / "squads.yaml").write_text(
        """squads:

  HelloWorldSquad:
    description: "Minimal squad — runs HelloWorldAgent and returns a greeting."
    agents:
      - HelloWorldAgent
    flow:
      - agent: HelloWorldAgent
        result_key: hello
"""
    )

    # config/config.yaml
    (base / "config" / "config.yaml").write_text(
        """inference:

  router:
    type: k9

  llm_factory:
    provider: ollama
    base_url: "${OLLAMA_BASE_URL:-http://localhost:11434}"

    models:
      general:
        model: "llama3.2:1b"
        temperature: 0.3
        max_tokens: 256

  model_catalog:
    default_model: general
    models:
      general:
        provider: ollama
        llm_ref: general
        capabilities: [general, chat]
        latency_tier: realtime
        cost_tier: minimal
"""
    )

    # api/app.py
    (base / "api" / "app.py").write_text(
        f"""# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import os, yaml, logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from k9_aif_abb.k9_agents.registry.agent_registry import AgentRegistry
from k9_aif_abb.k9_squad.squad_loader import SquadLoader
from agents.src.hello_world_agent import HelloWorldAgent
from orchestrators.hello_world_orchestrator import HelloWorldOrchestrator

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/config.yaml")
_SQUADS_YAML = os.path.join(os.path.dirname(__file__), "../config/squads.yaml")

with open(_CONFIG_PATH) as f:
    _config = yaml.safe_load(f)

_registry = AgentRegistry()
_registry.register("HelloWorldAgent", lambda: HelloWorldAgent(config=_config))
_squad = SquadLoader(_registry).load_one(_SQUADS_YAML, "HelloWorldSquad")
_orchestrator = HelloWorldOrchestrator(squad=_squad, config=_config)

app = FastAPI(title="K9-AIF {app_name}", version="1.0.0")

class HelloRequest(BaseModel):
    caller: Optional[str] = "n8n"
    message: Optional[str] = ""

@app.get("/")
def root():
    return {{"status": "ok", "endpoint": "POST /run"}}

@app.post("/run")
def run(payload: HelloRequest):
    try:
        result = _orchestrator.run(payload.model_dump())
        return JSONResponse(content={{"status": "success", "result": result}})
    except Exception as exc:
        log.error("Error: %s", exc)
        return JSONResponse(status_code=500, content={{"status": "error", "detail": str(exc)}})

@app.get("/health")
def health():
    return {{"status": "healthy"}}
"""
    )

    # Containerfile
    (base / "Containerfile").write_text(
        f"""FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir k9-aif uvicorn fastapi
COPY . .
EXPOSE {port}
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "{port}"]
"""
    )

    # build.sh
    build_sh = f"""#!/bin/bash
# Build the {app_name} container image
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"
IMAGE_NAME="{app_name}"
CONTAINER_NAME="{app_name}"
PORT={port}
echo "=== Building $IMAGE_NAME ==="
podman build -t $IMAGE_NAME .
echo ""
echo "=== Stopping existing container (if any) ==="
podman rm -f $CONTAINER_NAME 2>/dev/null || true
echo ""
echo "=== Starting $CONTAINER_NAME on port $PORT ==="
podman run -d --name $CONTAINER_NAME -p $PORT:$PORT --env K9_ENV=development $IMAGE_NAME
HOST_IP=$(hostname -I | awk '{{print $1}}')
echo ""
echo "=== Done ==="
echo "K9-AIF running at http://$HOST_IP:$PORT"
echo "Test: curl -X POST http://$HOST_IP:$PORT/run -H 'Content-Type: application/json' -d '{{\"caller\":\"test\"}}'"
"""
    (base / "build.sh").write_text(build_sh)
    (base / "build.sh").chmod(0o755)

    print()
    print(f"  ✓  {app_name}/ created with full K9-AIF n8n Hello World structure")
    print()
    print("Architecture rules enforced in the generated code:")
    print("  Router       → knows Orchestrators only")
    print("  Orchestrator → knows Squads only")
    print("  Squad        → knows Agents only")
    print("  Agent        → knows nothing above")
    print()
    print("Next steps:")
    print(f"  cd {app_name}")
    print(f"  k9aif inspect .        # verify architecture compliance before building")
    print(f"  bash build.sh          # build and run the container")
    print(f"  # In n8n: POST http://<your-ip>:{port}/run")
    print()
    print("Full example and docs: https://github.com/k9aif/examples")


def generate_cmd(topic: str):
    from pathlib import Path

    if not topic:
        print("Usage: k9aif --generate [n8n-hello-world | hello-world | agent | router | complete]")
        print(f"Available: n8n-hello-world, {', '.join(list(GENERATE_TEMPLATES.keys()) + ['complete'])}")
        return

    if topic == "n8n-hello-world":
        generate_n8n_hello_world()
        return

    if topic == "complete":
        generate_complete()
        return

    if topic not in GENERATE_TEMPLATES:
        print(f"Unknown template: {topic}")
        print(f"Available: {', '.join(list(GENERATE_TEMPLATES.keys()) + ['complete'])}")
        return

    filename = topic.replace("-", "_") + ".py"
    path = Path.cwd() / filename

    if path.exists():
        print(f"  ○  {filename} already exists — skipped")
        return

    path.write_text(GENERATE_TEMPLATES[topic])
    print(f"  ✓  {filename} created in {Path.cwd()}")
    print()
    print(f"Next:")
    print(f"  k9aif init        # create config.yaml if not done yet")
    print(f"  python {filename}")


def hello_world():
    """Print the Hello World agent code ready to run."""
    print("""# K9-AIF Hello World Agent
# Save as test.py and run: python test.py
# Requires: config.yaml (run 'k9aif init' first) + Ollama running

import yaml
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke


class HelloWorldAgent(BaseAgent):
    layer = "HelloWorldAgent SBB"

    def execute(self, payload: dict) -> dict:
        req = InferenceRequest(
            prompt=f"Say hello to {payload.get('name', 'World')} in one sentence.",
            task_type="general",
        )
        resp = llm_invoke(self.config, req)
        return {"agent": "HelloWorldAgent", "output": resp.output, "model": resp.model_alias}


if __name__ == "__main__":
    import yaml
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    agent = HelloWorldAgent(config=config)
    result = agent.execute({"name": "K9-AIF"})
    print(f"Output : {result['output']}")
    print(f"Model  : {result['model']}")
""")
    print("─" * 50)
    print("Steps:")
    print("  1. k9aif init              # creates config.yaml")
    print("  2. k9aif --hello-world > test.py   # save this code")
    print("  3. python test.py          # run it (needs Ollama)")


def doctor():
    """Check environment health — Python version, Ollama, dependencies."""
    import importlib
    print("K9-AIF Doctor — Environment Check")
    print("=" * 40)

    # Python version
    v = sys.version_info
    ok = v >= (3, 11)
    print(f"  {'✓' if ok else '✗'}  Python {v.major}.{v.minor}.{v.micro} {'(OK)' if ok else '(requires 3.11+)'}")

    # Package version
    try:
        from importlib.metadata import version as pkg_version
        try:
            v = pkg_version("k9-aif")
        except Exception:
            v = pkg_version("k9_aif_abb")
        print(f"  ✓  k9-aif {v}")
    except Exception:
        print("  ✗  k9-aif not installed")

    # Optional dependencies
    for pkg, label in [
        ("crewai",     "CrewAI (optional — for K9XLiteLLMBridgeAdapter)"),
        ("aiokafka",   "aiokafka (optional — for Kafka messaging)"),
        ("neo4j",      "neo4j (optional — for graph persistence)"),
        ("psycopg2",   "psycopg2 (optional — for PostgreSQL)"),
        ("chromadb",   "chromadb (optional — for vector store)"),
    ]:
        found = importlib.util.find_spec(pkg) is not None
        print(f"  {'✓' if found else '○'}  {label}")

    # Ollama reachability
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        print("  ✓  Ollama reachable at localhost:11434")
    except Exception:
        print("  ○  Ollama not reachable at localhost:11434 (optional — needed for LLM calls)")

    print()
    print("✓ = present   ○ = not found (optional)")


def init():
    """Scaffold a full K9-AIF project with folder structure + README."""
    from pathlib import Path

    cwd = Path.cwd()
    print(f"Initialising K9-AIF project in: {cwd}")
    print()

    # Generate full project structure
    generate_complete()

    # Generate README.md
    version = _version_str()
    readme = f"""\
# K9-AIF Project

Initialised with K9-AIF Framework v{version}

## What was created

```
main.py                      ← entry point — run this
config/
  config.yaml                ← LLM + inference config (mock LLM — no Ollama needed to start)
agents/
  src/
    my_agent.py              ← BaseAgent SBB — your first agent
orchestrators/
  my_orchestrator.py         ← BaseOrchestrator SBB
router/
  my_router.py               ← BaseRouter SBB
squads/
  my_squad.yaml              ← squad flow definition
runtime/                     ← routing state store (auto-created on first run)
```

## Run it

```bash
python main.py
```

No Ollama needed — uses mock LLM by default.
To use a real LLM, edit `config/config.yaml` and set your Ollama host.

## Upgrade to latest K9-AIF

```bash
pip install --upgrade k9-aif
k9aif --version
```

## Next steps

1. **Run the example**
   ```bash
   python main.py
   ```

2. **Add your own agent** — extend `BaseAgent` in `agents/src/`
   ```bash
   k9aif --generate agent
   ```

3. **Learn the framework**
   - `k9aif --help develop` — how to build agents, squads, orchestrators
   - `k9aif --help patterns` — architectural patterns in K9-AIF
   - `k9aif --help faq` — common questions

4. **Run the full test suite**
   ```bash
   k9aif verify
   k9aif doctor
   ```

5. **Explore the reference implementation**
   ```bash
   git clone https://github.com/k9aif/k9-aif-framework.git
   cd k9-aif-framework/examples/acme_support_center
   ```

## API Reference

Full pydoc API reference for `k9_aif_abb`:
https://pydocs.k9x.ai/pydocs/k9_aif_abb.html

## Links

| Resource | URL |
|---|---|
| Framework | https://github.com/k9aif/k9-aif-framework |
| Docs | https://k9x.ai |
| Blog | https://blog.k9x.ai |
| Architecture Graph | https://graph.k9x.ai |
| API Reference | https://pydocs.k9x.ai/pydocs/k9_aif_abb.html |
"""

    readme_path = cwd / "README.md"
    if readme_path.exists():
        print(f"  ○  README.md already exists — skipped")
    else:
        readme_path.write_text(readme)
        print(f"  ✓  README.md")

    print()
    print("Done. Run: python main.py")
    print()
    print("Ready to rumble!")


def _scan_subpackage(subpackage: str) -> list[tuple[str, str]]:
    """Dynamically discover classes in a k9_aif_abb subpackage."""
    import pkgutil
    import importlib
    import inspect

    results = []
    try:
        pkg = importlib.import_module(f"k9_aif_abb.{subpackage}")
        prefix = f"k9_aif_abb.{subpackage}."
        pkg_path = getattr(pkg, "__path__", [])

        for finder, mod_name, _ in pkgutil.walk_packages(pkg_path, prefix=prefix):
            try:
                mod = importlib.import_module(mod_name)
                for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                    if cls.__module__ == mod_name and not cls_name.startswith("_"):
                        results.append((cls_name, mod_name))
            except Exception:
                pass
    except Exception:
        pass

    return sorted(set(results))


def list_cmd(topic: str):
    """k9aif list [agents|core|factories|adapters|all] — dynamic discovery from installed package."""

    topic_map = {
        "core":      ["k9_core", "k9_squad"],
        "agents":    ["k9_agents"],
        "factories": ["k9_factories"],
        "adapters":  ["k9_adapters"],
        "all":       ["k9_core", "k9_squad", "k9_agents", "k9_factories", "k9_adapters"],
    }

    if topic not in topic_map:
        print(f"Unknown topic: {topic}")
        print(f"Usage: k9aif list [{' | '.join(topic_map.keys())}]")
        return

    print(f"K9-AIF — list {topic}  (discovered from installed package)")
    print("=" * 50)

    for subpkg in topic_map[topic]:
        classes = _scan_subpackage(subpkg)
        if classes:
            print(f"\n{subpkg}/")
            for cls_name, mod_name in classes:
                short_mod = mod_name.replace("k9_aif_abb.", "")
                print(f"  {cls_name:<40} {short_mod}")


def list_adapters():
    """List available K9-AIF adapters."""
    print("K9-AIF Available Adapters")
    print("=" * 40)

    adapters = [
        ("K9CrewAIAdapter",          "k9_aif_abb.k9_adapters.crewai.k9_crewai_adapter",          "Wrap a full CrewAI Crew in K9-AIF contracts"),
        ("K9XLiteLLMBridgeAdapter",  "k9_aif_abb.k9_adapters.crewai.k9x_litellm_bridge_adapter", "Wire K9ModelRouter into CrewAI agents (extends BaseLLM)"),
        ("MCPHttpConnector",          "k9_aif_abb.k9_core.integration.mcp_http_connector",        "HTTP/HTTPS MCP tool server client"),
        ("MCPStdioConnector",         "k9_aif_abb.k9_core.integration.mcp_stdio_connector",       "stdio MCP tool server client"),
    ]

    import importlib
    for name, module_path, description in adapters:
        found = importlib.util.find_spec(module_path.replace("/", ".")) is not None
        try:
            importlib.import_module(module_path)
            status = "✓"
        except Exception:
            status = "✗"
        print(f"  {status}  {name}")
        print(f"       {description}")
        print(f"       import: from {module_path} import {name}")
        print()

    print("Planned (roadmap):")
    print("  ○  K9XLangChainBridgeAdapter   — LangChain BaseLLM bridge")
    print("  ○  K9XOpenAIBridgeAdapter      — OpenAI-compatible bridge")
    print("  ○  K9XAnthropicBridgeAdapter   — Anthropic SDK bridge")


def inspect():
    """Inspect installed framework components."""
    import importlib

    print("K9-AIF Framework Inspection")
    print("=" * 40)

    components = {
        "ABB Contracts": [
            ("BaseAgent",               "k9_aif_abb.k9_core.agent.base_agent"),
            ("BaseRouter",              "k9_aif_abb.k9_core.router.base_router"),
            ("BaseOrchestrator",        "k9_aif_abb.k9_core.orchestration.base_orchestrator"),
            ("BaseSquad",               "k9_aif_abb.k9_squad.base_squad"),
            ("BaseModelRouter",         "k9_aif_abb.k9_inference.routers.base_model_router"),
            ("BaseValidationLoopAgent", "k9_aif_abb.k9_agents.validation"),
            ("BaseCriticActorAgent",    "k9_aif_abb.k9_agents.critic_actor"),
            ("BaseSecretManager",       "k9_aif_abb.k9_core.security.base_secret_manager"),
        ],
        "Factories": [
            ("LLMFactory",          "k9_aif_abb.k9_factories.llm_factory"),
            ("ModelRouterFactory",  "k9_aif_abb.k9_factories.model_router_factory"),
            ("SecretManagerFactory","k9_aif_abb.k9_factories.security_factory"),
            ("CacheFactory",        "k9_aif_abb.k9_factories.cache_factory"),
        ],
        "Adapters": [
            ("K9CrewAIAdapter",         "k9_aif_abb.k9_adapters.crewai.k9_crewai_adapter"),
            ("K9XLiteLLMBridgeAdapter", "k9_aif_abb.k9_adapters.crewai.k9x_litellm_bridge_adapter"),
        ],
    }

    for section, items in components.items():
        print(f"\n{section}:")
        for name, module in items:
            try:
                importlib.import_module(module)
                print(f"  ✓  {name}")
            except Exception as e:
                print(f"  ✗  {name} ({e})")


# ── Entry point ──────────────────────────────────────────────────────────────

HELP_MAIN += """
MORE COMMANDS:
  k9aif init                         Scaffold config.yaml + starter agent in current folder
  k9aif doctor                       Check environment — Python, Ollama, dependencies
  k9aif list [agents|core|factories|adapters|all]   List framework components
  k9aif inspect                      Inspect all installed framework components
  k9aif --generate hello-world       Generate hello_world.py in current folder
  k9aif --generate agent             Generate agent.py template
  k9aif --generate router            Generate router.py template
  k9aif --generate complete          Generate full project: router+orchestrator+squad+agent+config (mock LLM)
  k9aif new agent                    Scaffold a new agent (coming soon)
  k9aif new squad                    Scaffold a new squad  (coming soon)
"""

HELP_TOPICS = {
    "develop":  HELP_DEVELOP,
    "faq":      HELP_FAQ,
    "patterns": HELP_PATTERNS,
    "examples": HELP_EXAMPLES,
    "crewai":   HELP_CREWAI,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]

    if not args:
        print(HELP_MAIN.format(version=_version_str()))
        print()
        print("Ready to rumble!")
        print()
        return

    if args[0] in ("--help", "-h", "help"):
        topic = args[1] if len(args) > 1 else None
        if topic and topic in HELP_TOPICS:
            print(HELP_TOPICS[topic])
        elif topic:
            print(f"Unknown help topic: {topic}")
            print(f"Available: {', '.join(HELP_TOPICS.keys())}")
            sys.exit(1)
        else:
            print(HELP_MAIN.format(version=_version_str()))
            print()
            print("Ready to rumble!")
            print()
        return

    cmd = args[0]
    if cmd in ("--version", "-v"):
        version()
        return
    if cmd == "--hello-world":
        hello_world()
        return
    if cmd == "--generate":
        topic = args[1] if len(args) > 1 else ""
        generate_cmd(topic)
        return
    if cmd == "--context-init":
        context_init()
        return
    if cmd == "verify":
        verify()
    elif cmd == "version":
        version()
    elif cmd == "info":
        info()
    elif cmd == "doctor":
        doctor()
    elif cmd == "init":
        init()
    elif cmd == "list-adapters":
        list_adapters()
    elif cmd == "inspect":
        inspect()
    elif cmd == "list":
        topic = args[1] if len(args) > 1 else "all"
        list_cmd(topic)
    elif cmd == "new":
        topic = args[1] if len(args) > 1 else ""
        print(f"k9aif new {topic} — coming soon.")
        print("For now, use k9_generator.sh in the framework repository.")
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'k9aif --help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
