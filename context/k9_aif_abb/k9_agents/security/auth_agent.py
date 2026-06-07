# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from typing import Dict, Any
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class AuthAgent(BaseAgent):
    """
    AuthAgent
    ---------
    ABB security agent that validates inbound requests before orchestration.
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config or {})
        sec_cfg = self.config.get("security", {})
        self.api_key = sec_cfg.get("api_key")

    def check(self, request: Dict[str, Any]) -> bool:
        if not request or not isinstance(request, dict):
            raise ValueError("AuthAgent: invalid request format")

        if self.api_key:
            supplied = request.get("api_key")
            if supplied != self.api_key:
                raise ValueError("AuthAgent: API key missing or invalid")

        if not request.get("text") and not request.get("intent"):
            raise ValueError("AuthAgent: missing required fields")

        self.log("AuthAgent: request authenticated")
        return True

    def execute(self, request: dict) -> dict:
        if not request.get("text"):
            return {"answer": "Authentication failed: missing input"}

        self.check(request)
        return request  # forward unchanged