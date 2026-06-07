# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/integration/base_connector.py

from abc import ABC
from typing import Dict, Any, Optional
import logging
from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseConnector(BaseComponent, ABC):
    """
    K9-AIF Integration ABB - BaseConnector
    --------------------------------------
    Abstract base class for all Integration ABB connectors.
    Examples: RESTConnector, S3Connector, AppianConnector, etc.

    Responsibilities:
    - Provide consistent connect / send_request / close lifecycle.
    - Handle telemetry and monitoring through BaseComponent.
    - Offer unified, layer-aware logging (visible in console & log files).
    """

    layer = "Integration ABB"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        monitor=None,
    ):
        super().__init__(monitor=monitor)
        self.config = config or {}
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger("integration")

    async def log(self, msg: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(msg, level)
        line = f"[{self.layer}:{self.name}] {msg}"
        getattr(self.logger, level.lower(), self.logger.info)(line)

    # --- Default Lifecycle Methods ---

    def connect(self) -> bool:
        """Default no-op connect. Override in child if needed."""
        # Note: sync call, but we still log async-safe via logger directly.
        self.logger.debug(f"[{self.layer}:{self.name}] Default connect() called (no-op).")
        return True

    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Default no-op request. Override in child if needed."""
        self.logger.debug(f"[{self.layer}:{self.name}] Default send_request() called with {request}")
        return {"status": "noop", "input": request}

    def close(self) -> None:
        """Default no-op close. Override in child if needed."""
        self.logger.debug(f"[{self.layer}:{self.name}] Default close() called (no-op).")

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Default execute delegates to send_request()."""
        self.logger.debug(f"[{self.layer}:{self.name}] Executing payload via send_request: {payload}")
        return self.send_request(payload)