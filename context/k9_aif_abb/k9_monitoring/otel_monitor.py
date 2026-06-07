# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from k9_aif_abb.k9_core.monitoring.base_monitoring import BaseMonitor

from typing import Dict, Any

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

class OTelMonitor(BaseMonitor):
    def __init__(self, service_name: str = "k9_aif_app"):
        resource = Resource.create({"service.name": service_name})

        # Setup Tracer
        self.tracer_provider = TracerProvider(resource=resource)
        self.tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = trace.get_tracer(__name__)

        # Setup Metrics
        exporter = ConsoleMetricExporter()
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
        metrics.set_meter_provider(MeterProvider(metric_readers=[reader], resource=resource))
        self.meter = metrics.get_meter(__name__)

        # Example metric
        self.request_counter = self.meter.create_counter(
            name="requests_total",
            description="Total requests processed",
        )

    def emit_metric(self, name: str, value: float, tags: Dict[str, Any] | None = None) -> None:
        labels = tags or {}
        if name == "requests_total":
            self.request_counter.add(value, labels)

    def observe(self, event: str, meta: Dict[str, Any] | None = None) -> None:
        # Example trace span
        with self.tracer.start_as_current_span(event) as span:
            if meta:
                for k, v in meta.items():
                    span.set_attribute(k, str(v))