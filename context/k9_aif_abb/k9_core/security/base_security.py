# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/security/base_security.py

from typing import Any, Dict, Optional
import logging
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class BaseSecurityAgent(BaseAgent):
    """
    K9-AIF Security ABB - BaseSecurityAgent
    ---------------------------------------
    Abstract base class for all security-related agents in K9-AIF.
    Provides default stubs for authentication, authorization,
    redaction, and compliance validation.

    Responsibilities:
    - Establish the foundation for all Security/Guardian SBBs.
    - Integrate with BaseAgent for telemetry and unified logging.
    - Emit layer-aware messages visible in the live K9-AIF console.
    """

    layer = "Security ABB"

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 name: str = "BaseSecurityAgent", monitor=None):
        super().__init__(config=config, name=name, monitor=monitor)
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(message, level)
        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

    # ------------------------------------------------------------------
    # Default stub implementation
    # ------------------------------------------------------------------
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Stubbed execution method to be overridden by concrete SBBs."""
        self.logger.warning(f"[{self.layer}:{self.name}] Executing security checks (stubbed)")
        return {
            "status": "ok",
            "result": f"Stubbed response from {self.name}",
        }