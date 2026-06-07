# SPDX-License-Identifier: Apache-2.0
# k9x_studio — IntakeExtractorAgent (SpecParserAgent sub-agent, GREEN)

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from backend.services.spec_parsing_service import extract_intake


class IntakeExtractorAgent(BaseAgent):

    layer = "k9x_studio IntakeExtractorAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        content = payload.get("content", "")
        return {"agent": "IntakeExtractorAgent", "intake": extract_intake(content)}
