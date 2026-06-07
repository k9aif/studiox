# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework


from abc import ABC, abstractmethod
import logging
from typing import Optional


class BaseLoggingAgent(ABC):
    """
    K9-AIF Monitoring ABB - BaseLoggingAgent
    ----------------------------------------
    Abstract contract for all logging/monitoring agents in K9-AIF.
    Examples: ConsoleLogger, FileLogger, WebSocketLogger, PrometheusLogger.

    Responsibilities:
    - Define a unified log() interface for all monitoring agents.
    - Integrate with Python's logging system.
    - Serve as a bridge for ABB/SBB telemetry emission.
    """

    layer = "Monitoring ABB"

    def __init__(self, name: str = "BaseLoggingAgent"):
        self.name = name
        self.logger = logging.getLogger(name)

    @abstractmethod
    def log(self, message: str, level: str = "INFO"):
        """Emit a message to the configured monitoring target."""
        raise NotImplementedError

    def execute(self, message: str, level: str = "INFO"):
        """Unified entrypoint to emit a log message."""
        self.log(message, level)
        # Also mirror to the Python logger for consistency
        getattr(self.logger, level.lower(), self.logger.info)(
            f"[{self.layer}:{self.name}] {message}"
        )