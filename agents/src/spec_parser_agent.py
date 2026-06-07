# SPDX-License-Identifier: Apache-2.0
# k9x_studio — SpecParserAgent (K9SubAgentSpawner, GREEN)
#
# Spawns IntakeExtractorAgent, AgentExtractorAgent and ZoneMappingAgent in
# parallel via K9SubAgentSpawner.spawn_parallel — each works the same raw
# document content independently — then merges the three results into one
# "parsed" context for the LLMGrouping/Scoring/CanvasBuilder stages.

from typing import Any, Dict, Optional

from studio_agents.parallel.k9_sub_agent_spawner import K9SubAgentSpawner
from agents.src.intake_extractor_agent import IntakeExtractorAgent
from agents.src.agent_extractor_agent import AgentExtractorAgent
from agents.src.zone_mapping_agent import ZoneMappingAgent


class SpecParserAgent(K9SubAgentSpawner):

    layer = "k9x_studio SpecParserAgent SBB"

    _SUB_AGENTS = [IntakeExtractorAgent, AgentExtractorAgent, ZoneMappingAgent]

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        intake_result, agents_result, zones_result = self.spawn_parallel(self._SUB_AGENTS, payload)

        result = {
            "agent": "SpecParserAgent",
            "intake": intake_result.get("intake", {}),
            "agents_raw": agents_result.get("agents_raw", []),
            "zone_groups": zones_result.get("zone_groups", {"green": [], "ai": []}),
        }
        self.publish_event({
            "type": "SpecParsed",
            "agent": "SpecParserAgent",
            "agent_count": len(result["agents_raw"]),
        })
        return result
