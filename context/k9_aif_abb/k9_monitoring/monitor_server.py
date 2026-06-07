# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/monitoring/monitor_server.py

from typing import Dict, Any, Iterable, List, Optional
import logging
from k9_aif_abb.k9_core.monitoring.base_monitoring import BaseMonitor


class MonitorServer(BaseMonitor):
    """
    K9-AIF Monitoring ABB - MonitorServer
    -------------------------------------
    Multiplexes events and metrics to one or more concrete monitor backends
    (e.g., ConsoleMonitor, CloudWatchMonitor, PrometheusMonitor).

    Responsibilities:
    - Broadcasts metrics and observations to all attached monitors.
    - Adds common tags for environment, flow, or tenant context.
    - Ensures observability errors never interrupt functional execution.
    """

    layer = "Monitoring ABB"

    def __init__(
        self,
        monitors: Optional[Iterable[BaseMonitor]] = None,
        common_tags: Optional[Dict[str, Any]] = None,
        monitor: Optional[Any] = None,
    ):
        super().__init__(name="MonitorServer", monitor=monitor)
        self._monitors: List[BaseMonitor] = list(monitors or [])
        self._common = dict(common_tags or {})
        self.logger = logging.getLogger(self.name)

    def add(self, mon: BaseMonitor) -> None:
        """Attach a new monitor backend at runtime."""
        self._monitors.append(mon)
        self.logger.debug(f"[{self.layer}:{self.name}] Added monitor {mon.__class__.__name__}")

    # ------------------------------------------------------------------
    # Metric fan-out
    # ------------------------------------------------------------------
    def emit_metric(self, name: str, value: float, tags: Dict[str, Any] | None = None) -> None:
        merged = {**self._common, **(tags or {})}
        for m in self._monitors:
            try:
                m.emit_metric(name, value, merged)
            except Exception as e:
                self.logger.debug(f"[{self.layer}:{self.name}] emit_metric() failed on {m.__class__.__name__}: {e}")

    # ------------------------------------------------------------------
    # Event fan-out
    # ------------------------------------------------------------------
    def observe(self, event: str, meta: Dict[str, Any] | None = None) -> None:
        merged = {**self._common, **(meta or {})}
        for m in self._monitors:
            try:
                m.observe(event, merged)
            except Exception as e:
                self.logger.debug(f"[{self.layer}:{self.name}] observe() failed on {m.__class__.__name__}: {e}")

    # ------------------------------------------------------------------
    # Lifecycle fan-out
    # ------------------------------------------------------------------
    def start(self) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] Starting {len(self._monitors)} monitor(s)")
        for m in self._monitors:
            try:
                m.start()
            except Exception as e:
                self.logger.debug(f"[{self.layer}:{self.name}] start() failed on {m.__class__.__name__}: {e}")

    def flush(self) -> None:
        for m in self._monitors:
            try:
                m.flush()
            except Exception as e:
                self.logger.debug(f"[{self.layer}:{self.name}] flush() failed on {m.__class__.__name__}: {e}")

    def stop(self) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] Stopping {len(self._monitors)} monitor(s)")
        for m in self._monitors:
            try:
                m.stop()
            except Exception as e:
                self.logger.debug(f"[{self.layer}:{self.name}] stop() failed on {m.__class__.__name__}: {e}")