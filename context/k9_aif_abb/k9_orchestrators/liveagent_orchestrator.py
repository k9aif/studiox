# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_orchestrators/liveagent_orchestrator.py

import traceback
from typing import Dict, Any
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator


class LiveAgentOrchestrator(BaseOrchestrator):
    """
    K9-AIF LiveAgentOrchestrator ABB
    --------------------------------
    Routes user interactions to a human support channel
    (e.g., Slack, Teams, ServiceNow, or call center bridge).
    """

    layer = "LiveAgent Orchestrator ABB"

    async def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("LiveAgentOrchestrator execution started")

        try:
            query = payload.get("message", "")

            if self.message_bus:
                try:
                    self.message_bus.publish({
                        "event_type": "escalation_start",
                        "agent": self.__class__.__name__,
                        "layer": self.layer,
                        "query": query,
                        "status": "initiated",
                    })
                except Exception:
                    pass

            reply = (
                "**LiveAgentOrchestrator**\n"
                "Your query has been forwarded to a human support specialist.\n\n"
                f"**Summary:** {query}\n"
                "A Live Agent will follow up shortly."
            )

            if self.message_bus:
                try:
                    self.message_bus.publish({
                        "event_type": "escalation_triggered",
                        "agent": self.__class__.__name__,
                        "layer": self.layer,
                        "status": "initiated",
                    })
                except Exception:
                    pass

            self.logger.info("[OK] LiveAgent escalation initiated")
            return {"reply": reply}

        except Exception as e:
            self.logger.error(f"[ERROR] LiveAgent orchestration error: {e}")
            traceback.print_exc()
            return {"reply": "[WARN] Live agent escalation failed."}
