# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# k9_aif_abb/k9_monitoring/prometheus_monitor.py

from typing import Dict, Any, Optional
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, push_to_gateway, start_http_server
import time
import threading

from k9_aif_abb.k9_core.monitoring.base_monitoring import BaseMonitor


class PrometheusMonitor(BaseMonitor):
    def __init__(self, port: int = 8001, pushgateway: Optional[str] = None):
        self.port = port
        self.pushgateway = pushgateway  # e.g., "http://localhost:9091"

        self.registry = CollectorRegistry()

        # Define core metrics
        self.requests = Counter(
            "k9aif_requests_total",
            "Total requests processed",
            ["flow", "agent"],
            registry=self.registry,
        )
        self.failures = Counter(
            "k9aif_failures_total",
            "Total failed requests",
            ["flow", "agent"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "k9aif_request_latency_seconds",
            "Request latency in seconds",
            ["flow", "agent"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
            registry=self.registry,
        )
        self.active = Gauge(
            "k9aif_active_requests",
            "Number of active requests",
            ["flow"],
            registry=self.registry,
        )

        self._server_started = False
        self._lock = threading.Lock()

    # --- BaseMonitor interface ---
    def emit_metric(self, name: str, value: float, tags: Dict[str, Any] | None = None) -> None:
        """Generic metric emitter for custom metrics."""
        tags = tags or {}
        if name == "requests_total":
            self.requests.labels(flow=tags.get("flow", "default"), agent=tags.get("agent", "unknown")).inc(value)
        elif name == "failures_total":
            self.failures.labels(flow=tags.get("flow", "default"), agent=tags.get("agent", "unknown")).inc(value)
        elif name == "active":
            self.active.labels(flow=tags.get("flow", "default")).inc(value)

        if self.pushgateway:
            push_to_gateway(self.pushgateway, job="k9aif", registry=self.registry)

    def observe(self, event: str, meta: Dict[str, Any] | None = None) -> None:
        """Higher-level event observation (e.g., request complete)."""
        meta = meta or {}
        flow = meta.get("flow", "default")
        agent = meta.get("agent", "unknown")
        duration = meta.get("duration", 0.0)
        success = meta.get("success", True)

        self.requests.labels(flow=flow, agent=agent).inc()
        if not success:
            self.failures.labels(flow=flow, agent=agent).inc()
        self.latency.labels(flow=flow, agent=agent).observe(duration)

        if self.pushgateway:
            push_to_gateway(self.pushgateway, job="k9aif", registry=self.registry)

    # --- Server management ---
    def start(self) -> None:
        """Start Prometheus scrape endpoint (only once)."""
        with self._lock:
            if not self._server_started:
                start_http_server(self.port, registry=self.registry)
                self._server_started = True
                print(f"[PrometheusMonitor] Serving metrics at http://localhost:{self.port}/metrics")

    def track_active(self, flow: str, delta: int = 1) -> None:
        """Increment or decrement active request gauge."""
        self.active.labels(flow=flow).inc(delta)