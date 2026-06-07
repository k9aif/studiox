# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_monitoring/cloudwatch_monitor.py

import boto3
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from k9_aif_abb.k9_core.monitoring.base_monitoring import BaseMonitor


class CloudWatchMonitor(BaseMonitor):
    """
    K9-AIF Monitoring SBB - CloudWatchMonitor
    -----------------------------------------
    Specialized Business Block that publishes metrics and events
    from K9-AIF components into AWS CloudWatch.

    Responsibilities:
    - Implements BaseMonitor (emit_metric, observe, lifecycle hooks).
    - Sends structured telemetry to CloudWatch Metrics and Logs.
    - Provides layer-aware visibility for distributed deployments.
    """

    layer = "Monitoring ABB"

    def __init__(self,
                 namespace: str = "K9AIF",
                 region_name: str = "us-east-1",
                 monitor: Optional[Any] = None):
        super().__init__(name="CloudWatchMonitor", monitor=monitor)
        self.namespace = namespace
        self.region_name = region_name
        self.logger = logging.getLogger("cloudwatch")
        try:
            self.client = boto3.client("cloudwatch", region_name=region_name)
            self.logger.info(f"[{self.layer}:{self.name}] Initialized CloudWatch client in {region_name}")
        except Exception as e:
            self.client = None
            self.logger.warning(f"[{self.layer}:{self.name}] Failed to init CloudWatch client: {e}")

    # ------------------------------------------------------------------
    # Metric emission
    # ------------------------------------------------------------------
    def emit_metric(self, name: str, value: float, tags: Dict[str, Any] | None = None) -> None:
        """Publish a numeric metric to CloudWatch."""
        if not self.client:
            self.logger.debug(f"[{self.layer}:{self.name}] Metric '{name}'={value} (client not initialized)")
            return

        dimensions = [{"Name": k, "Value": str(v)} for k, v in (tags or {}).items()]
        metric_data = [{
            "MetricName": name,
            "Timestamp": datetime.utcnow(),
            "Value": value,
            "Unit": "None",
            "Dimensions": dimensions
        }]

        try:
            self.client.put_metric_data(Namespace=self.namespace, MetricData=metric_data)
            self.logger.info(f"[{self.layer}:{self.name}] Sent metric {name}={value} to CloudWatch")
        except Exception as e:
            self.logger.error(f"[{self.layer}:{self.name}] Failed to send metric {name}: {e}")

    # ------------------------------------------------------------------
    # Event observation
    # ------------------------------------------------------------------
    def observe(self, event: str, meta: Dict[str, Any] | None = None) -> None:
        """Record structured events or logs."""
        details = {"event": event, "meta": meta or {}}
        self.logger.info(f"[{self.layer}:{self.name}] Observed event: {details}")
        # Optional: integrate with CloudWatch Logs via boto3 logs client

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def start(self) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] CloudWatch monitor started")

    def flush(self) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] flush() called (no buffer)")

    def stop(self) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] CloudWatch monitor stopped")