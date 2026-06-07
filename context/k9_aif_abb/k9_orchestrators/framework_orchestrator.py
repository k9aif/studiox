# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_orchestrators/framework_orchestrator.py

import traceback
from typing import Any, Dict

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator


class FrameworkOrchestrator(BaseOrchestrator):
    """
    K9-AIF FrameworkOrchestrator ABB
    --------------------------------
    Default orchestrator for K9-AIF technical queries.
    Invoked by RouterAgent when intent = k9_technical.

    Responsibilities:
      - Validate orchestration flow
      - Log routing and orchestration lifecycle events
      - Delegate downstream to retriever or LLM as needed
    """

    layer = "Framework Orchestrator ABB"

    async def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a governed orchestration flow."""
        self.logger.info("FrameworkOrchestrator execution started")

        try:
            query = payload.get("message", "")

            # Publish routing event
            if self.message_bus:
                event = {
                    "event_type": "orchestration_start",
                    "agent": self.__class__.__name__,
                    "layer": self.layer,
                    "query": query,
                    "status": "started",
                }
                try:
                    self.message_bus.publish(event)
                except Exception:
                    pass

            # ------------------------------------------------------------------
            # Core orchestration logic (simple demo)
            # ------------------------------------------------------------------
            reply = (
                f"[INFO] K9-AIF FrameworkOrchestrator\n"
                f"Your question was routed successfully through the governed flow.\n\n"
                f"**Query:** {query}\n"
                f"**Handler:** {self.__class__.__name__}\n"
                f"**Layer:** {self.layer}\n"
            )

            # Publish orchestration completion event
            if self.message_bus:
                completion = {
                    "event_type": "orchestration_complete",
                    "agent": self.__class__.__name__,
                    "layer": self.layer,
                    "status": "completed",
                }
                try:
                    self.message_bus.publish(completion)
                except Exception:
                    pass

            self.logger.info("[OK] FrameworkOrchestrator execution complete")
            return {"reply": reply}

        except Exception as e:
            self.logger.error(f"[ERROR] Orchestrator error: {e}")
            traceback.print_exc()
            return {"reply": "[WARN] Framework orchestration failed."}
