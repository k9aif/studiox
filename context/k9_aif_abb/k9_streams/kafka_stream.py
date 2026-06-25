# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""KafkaEventFabric — Kafka / Confluent / Redpanda / IBM Event Streams SBB."""

import json
import logging
import os
import threading
from typing import Any, Callable, Dict, Optional

from k9_aif_abb.k9_core.streams.base_event_fabric import BaseEventFabric
from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope

log = logging.getLogger("KafkaEventFabric")


class KafkaEventFabric(BaseEventFabric):
    """
    Kafka-backed event fabric SBB.

    Compatible with Apache Kafka, Confluent Platform, Confluent Cloud,
    Redpanda, and IBM Event Streams — all Kafka-protocol compatible.

    Credentials are never in config.yaml — use environment variables:
      KAFKA_BOOTSTRAP_SERVERS   broker addresses (default: localhost:9092)
      KAFKA_SASL_USERNAME       for SASL_SSL security protocol
      KAFKA_SASL_PASSWORD       for SASL_SSL security protocol

    Requires: pip install k9-aif[kafka]

    YAML config::

        streams:
          enabled: true
          provider: kafka
          kafka:
            bootstrap_servers: "${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
            security_protocol: PLAINTEXT    # PLAINTEXT | SASL_SSL
            sasl_mechanism:    PLAIN        # PLAIN | SCRAM-SHA-256 | SCRAM-SHA-512
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._producer = None
        self._consumers: Dict[str, Any] = {}
        self._consumer_threads: Dict[str, threading.Thread] = {}
        self._kafka_cfg = self.config.get("streams", {}).get("kafka", {})

    def _bootstrap_servers(self) -> str:
        return self._kafka_cfg.get(
            "bootstrap_servers",
            os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        )

    def _security_kwargs(self) -> Dict[str, Any]:
        protocol = self._kafka_cfg.get("security_protocol", "PLAINTEXT")
        if protocol == "PLAINTEXT":
            return {"security_protocol": "PLAINTEXT"}
        return {
            "security_protocol": protocol,
            "sasl_mechanism":    self._kafka_cfg.get("sasl_mechanism", "PLAIN"),
            "sasl_plain_username": os.environ.get("KAFKA_SASL_USERNAME", ""),
            "sasl_plain_password": os.environ.get("KAFKA_SASL_PASSWORD", ""),
        }

    def _ensure_producer(self) -> None:
        if self._producer is not None:
            return
        try:
            from kafka import KafkaProducer  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pip install k9-aif[kafka] required for KafkaEventFabric") from exc

        self._producer = KafkaProducer(
            bootstrap_servers=self._bootstrap_servers(),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            **self._security_kwargs(),
        )
        log.info("[KafkaFabric] Producer connected to %s", self._bootstrap_servers())

    def publish(self, envelope: EventEnvelope, topic: str) -> None:
        self._ensure_producer()
        self._producer.send(topic, value=envelope.to_dict())
        log.debug("[KafkaFabric] Published %s → %s", envelope.event_type, topic)

    def subscribe(self, topic: str, callback: Callable[[EventEnvelope], None]) -> None:
        try:
            from kafka import KafkaConsumer  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pip install k9-aif[kafka] required for KafkaEventFabric") from exc

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers(),
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            **self._security_kwargs(),
        )
        self._consumers[topic] = consumer

        def _consume() -> None:
            log.info("[KafkaFabric] Consumer started on topic: %s", topic)
            for msg in consumer:
                try:
                    envelope = EventEnvelope.from_dict(msg.value)
                    callback(envelope)
                except Exception as exc:
                    log.error("[KafkaFabric] Error on %s: %s", topic, exc)

        thread = threading.Thread(target=_consume, daemon=True, name=f"k9-stream-{topic}")
        self._consumer_threads[topic] = thread
        thread.start()

    def unsubscribe(self, topic: str) -> None:
        consumer = self._consumers.pop(topic, None)
        if consumer:
            consumer.close()
        self._consumer_threads.pop(topic, None)

    def close(self) -> None:
        if self._producer:
            self._producer.close()
            self._producer = None
        for consumer in self._consumers.values():
            consumer.close()
        self._consumers.clear()
        self._consumer_threads.clear()
