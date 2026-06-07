# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/logging/logging_agent.py

from typing import Dict, Any, Optional
from k9_aif_abb.k9_core.logging.base_logger import BaseLoggingAgent


class LoggingAgent(BaseLoggingAgent):
    """
    K9-AIF LoggingAgent
    -------------------
    ABB-level logging agent for emitting structured log messages.

    Responsibilities:
    - Emit log messages via unified logging interface
    - Integrate with Python logging system
    - Serve as a bridge for monitoring/telemetry
    """

    layer = "Logging ABB"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        name = cfg.get("logging", {}).get("name", "LoggingAgent")
        super().__init__(name=name)
        self.config = cfg

    def log(self, message: str, level: str = "INFO"):
        """
        Emit a log message using the configured logging backend.
        """
        getattr(self.logger, level.lower(), self.logger.info)(
            f"[{self.layer}:{self.name}] {message}"
        )