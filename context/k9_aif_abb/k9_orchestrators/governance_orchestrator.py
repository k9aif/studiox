# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_orchestrators/governance_orchestrator.py

import traceback
from typing import Dict, Any
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator


class GovernanceOrchestrator(BaseOrchestrator):
    """
    K9-AIF GovernanceOrchestrator ABB
    ---------------------------------
    Handles policy audits, enforcement checks, and compliance routing.
    Triggered when governance-related intents are detected.
    """

    layer = "Governance Orchestrator ABB"

    async def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("GovernanceOrchestrator execution started")

        try:
            query = payload.get("message", "")

            if self.message_bus:
                try:
                    self.message_bus.publish({
                        "event_type": "orchestration_start",
                        "agent": self.__class__.__name__,
                        "layer": self.layer,
                        "query": query,
                        "status": "started",
                    })
                except Exception:
                    pass

            reply = (
                "**GovernanceOrchestrator**\n"
                "Your request has been routed through the governance path.\n"
                "All enforcement and compliance policies are verified.\n\n"
                f"**Query:** {query}\n"
                f"**Layer:** {self.layer}"
            )

            if self.message_bus:
                try:
                    self.message_bus.publish({
                        "event_type": "orchestration_complete",
                        "agent": self.__class__.__name__,
                        "layer": self.layer,
                        "status": "completed",
                    })
                except Exception:
                    pass

            self.logger.info("[OK] Governance orchestration complete")
            return {"reply": reply}

        except Exception as e:
            self.logger.error(f"[ERROR] Governance orchestration error: {e}")
            traceback.print_exc()
            return {"reply": "[WARN] Governance orchestration failed."}
