# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_monitoring/console_monitor.py

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.monitoring.base_monitoring import BaseMonitor


class ConsoleMonitor(BaseMonitor):
    """
    K9-AIF Monitoring SBB - ConsoleMonitor
    --------------------------------------
    Lightweight monitor backend that logs metrics and events
    directly to stdout or the framework logger.

    Responsibilities:
    - Provides immediate feedback for developers.
    - Serves as the default local monitor in non-cloud environments.
    """

    layer = "Monitoring SBB"

    def __init__(self, name: str = "ConsoleMonitor", monitor: Optional[Any] = None):
        super().__init__(name=name, monitor=monitor)
        self.logger = logging.getLogger(self.name)

    def emit_metric(self, name: str, value: float, tags: Dict[str, Any] | None = None) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "metric": name,
            "value": value,
            "tags": tags or {},
        }
        self.logger.info(f"[{self.layer}:{self.name}] {json.dumps(record)}")

    def observe(self, event: str, meta: Dict[str, Any] | None = None) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "meta": meta or {},
        }
        self.logger.info(f"[{self.layer}:{self.name}] {json.dumps(record)}")

    def start(self) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] ConsoleMonitor started")

    def flush(self) -> None:
        # No buffering; nothing to flush
        pass

    def stop(self) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] ConsoleMonitor stopped")