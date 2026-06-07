# SPDX-License-Identifier: Apache-2.0
# k9x_studio — SpecImportOrchestrator (SBB)
#
# Coordinates SpecImportSquad for the "spec_import" event. Knows only its
# squad ID — loaded via _load_squad() — never the router or other
# orchestrators (three-level decoupling, see CLAUDE.md).

from pathlib import Path
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator
from k9_aif_abb.k9_agents.registry.agent_registry import AgentRegistry
from k9_aif_abb.k9_squad.squad_loader import SquadLoader

from agents.agent_config_loader import AgentConfigLoader
from agents.src.governance_agent import GovernanceAgent
from agents.src.spec_parser_agent import SpecParserAgent
from agents.src.llm_grouping_agent import LLMGroupingAgent
from agents.src.scoring_agent import ScoringAgent
from agents.src.canvas_builder_agent import CanvasBuilderAgent

_SQUAD_ID = "SpecImportSquad"
_SQUAD_YAML = Path(__file__).resolve().parent.parent / "squads" / "yaml" / "spec_import_squad.yaml"

_AGENT_CLASSES = [
    ("GovernanceAgent", GovernanceAgent),
    ("SpecParserAgent", SpecParserAgent),
    ("LLMGroupingAgent", LLMGroupingAgent),
    ("ScoringAgent", ScoringAgent),
    ("CanvasBuilderAgent", CanvasBuilderAgent),
]


class SpecImportOrchestrator(BaseOrchestrator):

    layer = "k9x_studio SpecImportOrchestrator SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)
        self._squad = self._load_squad()

    # ------------------------------------------------------------------
    def _load_squad(self):
        registry = AgentRegistry()
        loader = AgentConfigLoader()
        for name, cls in _AGENT_CLASSES:
            registry.register(
                name,
                lambda c=cls, n=name: c(config=loader.merge_with_global(n, self.config)),
            )
        return SquadLoader(registry).load_one(_SQUAD_YAML, _SQUAD_ID)

    # ------------------------------------------------------------------
    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self._squad.execute(payload)

        governance = result.get("governance", {})
        if not governance.get("passed", True):
            self.publish_status("FlowBlocked", {
                "squad_id": _SQUAD_ID,
                "correlation_id": payload.get("correlation_id"),
                "reason": governance.get("reason"),
            })
            return {
                "status": "blocked",
                "reason": governance.get("reason") or "[BLOCKED] document failed governance screen",
            }

        canvas = result.get("canvas", {})
        self.publish_status("FlowCompleted", {
            "squad_id": _SQUAD_ID,
            "correlation_id": payload.get("correlation_id"),
            "result_summary": result.get("status"),
        })
        return {"status": "completed", **canvas}

    # ------------------------------------------------------------------
    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for execute_flow — matches the Router → Orchestrator.run(event) convention."""
        return self.execute_flow(event)
