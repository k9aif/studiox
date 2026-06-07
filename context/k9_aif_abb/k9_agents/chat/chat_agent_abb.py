# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/chat/chat_agent_abb.py

import traceback
from typing import Dict, Any
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class ChatAgentABB(BaseAgent):
    """
    K9-AIF Chat Agent ABB - Governed Conversational Agent
    ----------------------------------------------------
    Provides the core orchestration and governance for all ChatAgents.
    Ensures:
      - Governance enforcement via BaseAgent.enforce_governance()
      - Logging and audit events to MessageBus
      - Optional retrieval or LLM delegation handled by SBB subclass
    """

    layer = "Chat Agent ABB"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes governed ABB-level chat flow."""
        self.logger.info("[%s] execution started", self.layer)

        # ---------------- Governance Enforcement ----------------
        try:
            self.enforce_governance()
            self.logger.info("[%s] governance enforcement passed", self.layer)
        except PermissionError as e:
            self.logger.error("[%s] %s", self.layer, e)
            return {"reply": "[WARN] Governance enforcement failed — no governance pipeline configured."}

        # ---------------- Input Validation ----------------
        if not payload or "message" not in payload:
            self.logger.error("[%s] Missing 'message' in payload", self.layer)
            return {"reply": "[WARN] No message provided."}

        query = payload["message"]

        # ---------------- Core Processing ----------------
        try:
            self._publish({"event_type": "chat_request_received", "query": query, "status": "received"})

            # ABB baseline reply — SBB subclasses override execute() to replace this.
            base_reply = (
                f"[{self.layer}] Your message has been received and is "
                f"routed through K9-AIF governance.\nMessage: {query}"
            )

            self._publish({"event_type": "chat_cycle_complete", "status": "completed"})
            self.logger.info("[%s] cycle completed", self.layer)
            return {"reply": base_reply}

        except Exception as e:
            self.logger.error("[%s] runtime error: %s", self.layer, e)
            traceback.print_exc()
            return {"reply": "[WARN] Internal chat processing error."}

    # ------------------------------------------------------------------
    def _publish(self, event: Dict[str, Any]) -> None:
        """Publish an audit event to the message bus if one is wired up."""
        if not self.message_bus:
            return
        try:
            self.message_bus.publish({
                "layer": self.layer,
                "agent": self.__class__.__name__,
                **event,
            })
        except Exception:
            pass