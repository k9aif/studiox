# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""BaseEventFabric — transport-agnostic ABB contract for the K9 enterprise context fabric."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope


class BaseEventFabric(ABC):
    """
    Transport-agnostic ABB contract for the K9 enterprise context fabric.

    The fabric is the governed transport layer that carries continuously
    streaming enterprise context — SAP, CRM, CDC, IoT telemetry, workflow
    transitions — to agentic flows in real time.

    SBBs implement this for specific providers:
      KafkaEventFabric      — Kafka / Confluent / Redpanda / IBM Event Streams
      InMemoryEventFabric   — local testing, zero external dependencies

    Kafka and Confluent are SBBs. K9-AIF defines how agentic flows use them.

    YAML config::

        streams:
          enabled: true
          provider: kafka           # kafka | in_memory (default)
          kafka:
            bootstrap_servers: "${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def publish(self, envelope: EventEnvelope, topic: str) -> None:
        """Publish an event envelope to the fabric on the given topic."""
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[EventEnvelope], None]) -> None:
        """Subscribe to a topic; callback fires for each arriving envelope."""
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, topic: str) -> None:
        """Cancel subscription to a topic."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Release all resources held by this fabric instance."""
        raise NotImplementedError
