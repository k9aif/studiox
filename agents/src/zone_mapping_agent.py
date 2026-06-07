# SPDX-License-Identifier: Apache-2.0
# k9x_studio — ZoneMappingAgent (SpecParserAgent sub-agent, GREEN)
#
# Re-derives the agent register independently of AgentExtractorAgent so it
# can run fully in parallel (no dependency on another sub-agent's output),
# then groups it by governance zone for the rule-based canvas suggestion.

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from backend.services.spec_parsing_service import extract_agents_raw, group_by_zone


class ZoneMappingAgent(BaseAgent):

    layer = "k9x_studio ZoneMappingAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        content = payload.get("content", "")
        zone_groups = group_by_zone(extract_agents_raw(content))
        return {"agent": "ZoneMappingAgent", "zone_groups": zone_groups}
