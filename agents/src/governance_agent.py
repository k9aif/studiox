# SPDX-License-Identifier: Apache-2.0
# k9x_studio — GovernanceAgent (SpecImportSquad gate, GREEN)

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from backend.services.spec_parsing_service import governance_check


class GovernanceAgent(BaseAgent):

    layer = "k9x_studio GovernanceAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        content = payload.get("content", "")
        reason = governance_check(content)

        result = {
            "agent": "GovernanceAgent",
            "passed": reason is None,
            "reason": reason,
        }
        self.publish_event({"type": "GovernanceScreened", "agent": "GovernanceAgent", "passed": result["passed"]})
        return result
