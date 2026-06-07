# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/monitoring/base_monitor.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import asyncio
from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseMonitor(BaseComponent, ABC):
    """
    K9-AIF Monitoring ABB - BaseMonitor
    -----------------------------------
    Stable interface for metrics and event emission across back-ends
    (Prometheus, Grafana, OpenTelemetry, WebSocket stream, etc.).
    """

    layer = "Monitoring ABB"

    def __init__(self, name: str = "BaseMonitor", monitor=None):
        # monitor param is normally None; kept for interface symmetry
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)

    # ---------- Core Abstract Methods ----------
    @abstractmethod
    def emit_metric(self, name: str, value: float,
                    tags: Optional[Dict[str, Any]] = None) -> None:
        """Emit a single numeric metric."""
        raise NotImplementedError

    @abstractmethod
    def observe(self, event: str,
                meta: Optional[Dict[str, Any]] = None) -> None:
        """Record an observation or structured event."""
        raise NotImplementedError

    # ---------- Optional Lifecycle Hooks ----------
    def start(self) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] start() called (no-op)")

    def flush(self) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] flush() called (no-op)")

    def stop(self) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] stop() called (no-op)")

    # ---------- Logging Convenience ----------
    async def log(self, message: str, level: str = "INFO"):
        """
        Layer-aware async log; streams to console and Python logger.
        Safe to extend with lazy imports (e.g., MonitorFactory) if needed later.
        """
        try:
            await super().log(message, level)
        except Exception:
            # If BaseComponent.log not async, fallback gracefully
            formatted = f"[{self.layer}:{self.name}] {message}"
            getattr(self.logger, level.lower(), self.logger.info)(formatted)

        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)