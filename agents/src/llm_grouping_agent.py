# SPDX-License-Identifier: Apache-2.0
# k9x_studio — LLMGroupingAgent (AMBER — calls the user-configured LLM)
#
# Asks the transient, per-request LLM session (never persisted — see
# LlmSessionConfig in the original routes.py) to group the extracted agent
# register into squads. Returns no suggestion when the session isn't
# configured, the call fails, or the response can't be parsed as JSON —
# ScoringAgent always has the rule-based grouping to fall back to.

import json
import re
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from backend.services.spec_parsing_service import call_llm, is_local_blocked
from backend.services.context_service import get_llm_context

_FENCE_RE = re.compile(r"```(?:json)?")
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class LLMGroupingAgent(BaseAgent):

    layer = "k9x_studio LLMGroupingAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        parsed = payload.get("parsed", {})
        agents_raw = parsed.get("agents_raw", [])
        llm_config = payload.get("llm_config")

        if not llm_config or not agents_raw:
            return {"agent": "LLMGroupingAgent", "suggestion": None, "source": None}

        try:
            cfg = json.loads(llm_config)
        except (TypeError, ValueError):
            return {"agent": "LLMGroupingAgent", "suggestion": None, "source": None}

        endpoint = (cfg.get("endpoint") or "").strip().rstrip("/")
        provider = (cfg.get("provider") or "ollama").strip()
        model    = (cfg.get("model") or "granite3.3:2b").strip()
        api_key  = cfg.get("api_key", "")

        if not endpoint or is_local_blocked(endpoint):
            return {"agent": "LLMGroupingAgent", "suggestion": None, "source": None}
        if not endpoint.startswith(("http://", "https://")):
            endpoint = "http://" + endpoint

        intake = parsed.get("intake", {})
        task_list = "\n".join(
            f"- {a['name']} [{a['zone']}]: {a['description']}" for a in agents_raw
        )
        prompt = f"""{get_llm_context()}

---

## Spec document agents to organise into K9-AIF squads

Process: {intake.get('project_name', 'Process')}
Domain: {intake.get('domain', '')}
Agents extracted from the specification:
{task_list}

Group these agents into logical squads. Each squad represents a distinct workflow stage.
Assign the correct agent type (BaseAgent for GREEN/deterministic, K9ValidationLoopAgent for AMBER, K9CriticActorAgent for RED/high-risk).
Identify 2-4 logical groupings — never put all agents in one squad.

Return ONLY a JSON object — no explanation, no markdown, no code fences:
{{
  "orchestrators": [{{"name": "ExampleOrchestrator"}}],
  "squads": [{{"name": "ExampleSquad", "agents": ["AgentOne", "AgentTwo"]}}],
  "agents": [{{"name": "AgentOne", "type": "BaseAgent", "model": "general", "description": "What this agent does"}}]
}}

Every agent name in squads[].agents must have a matching entry in agents[]. Return ONLY valid JSON.
"""

        try:
            raw_text = call_llm(endpoint, provider, model, api_key, prompt)
            raw_text = _FENCE_RE.sub("", raw_text).strip()
            match = _JSON_RE.search(raw_text)
            if not match:
                return {"agent": "LLMGroupingAgent", "suggestion": None, "source": None}

            suggestion = json.loads(match.group())
            if "agents" not in suggestion or "squads" not in suggestion:
                return {"agent": "LLMGroupingAgent", "suggestion": None, "source": None}

            self.publish_event({"type": "LLMGroupingProposed", "agent": "LLMGroupingAgent",
                                "agent_count": len(suggestion.get("agents", []))})
            return {"agent": "LLMGroupingAgent", "suggestion": suggestion, "source": "llm"}
        except Exception as exc:
            self.logger.warning("[%s] LLM grouping unavailable: %s", self.layer, exc)
            return {"agent": "LLMGroupingAgent", "suggestion": None, "source": None}
