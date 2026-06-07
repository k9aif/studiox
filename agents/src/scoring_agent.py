# SPDX-License-Identifier: Apache-2.0
# k9x_studio — ScoringAgent (GREEN — picks the winning canvas suggestion)

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from backend.services.spec_parsing_service import (
    build_suggestion_from_zones,
    default_suggestion,
    score_suggestion,
)

_EMPTY_SCORE = {"score": 0, "agent_count": 0, "squad_count": 0, "type_count": 0}


class ScoringAgent(BaseAgent):

    layer = "k9x_studio ScoringAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        parsed = payload.get("parsed", {})
        intake = parsed.get("intake", {})
        agents_raw = parsed.get("agents_raw", [])
        zone_groups = parsed.get("zone_groups", {"green": [], "ai": []})
        llm_grouping = payload.get("llm_grouping", {}) or {}
        llm_suggestion = llm_grouping.get("suggestion")

        project_name = intake.get("project_name", "Project")

        if not agents_raw:
            return {
                "agent": "ScoringAgent",
                "suggestion": default_suggestion(project_name, intake.get("domain", "")),
                "source": "spec-fallback",
                "scoring": None,
            }

        rule_suggestion = build_suggestion_from_zones(project_name, zone_groups)

        if llm_suggestion is None:
            return {
                "agent": "ScoringAgent",
                "suggestion": rule_suggestion,
                "source": "spec",
                "scoring": None,
            }

        llm_scores = score_suggestion(llm_suggestion)
        rule_scores = score_suggestion(rule_suggestion) if rule_suggestion.get("agents") else dict(_EMPTY_SCORE)

        if llm_scores["score"] >= rule_scores["score"]:
            winner, suggestion, source = "llm", llm_suggestion, "spec+llm"
        else:
            winner, suggestion, source = "rule_based", rule_suggestion, "spec"

        self.publish_event({"type": "SuggestionScored", "agent": "ScoringAgent", "winner": winner})
        return {
            "agent": "ScoringAgent",
            "suggestion": suggestion,
            "source": source,
            "scoring": {"winner": winner, "llm": llm_scores, "rule_based": rule_scores},
        }
