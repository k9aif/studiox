# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/message_factory.py

from __future__ import annotations
from typing import Any, Dict
import logging, threading, json

from k9_aif_abb.k9_core.messaging.k9_event_bus import K9EventBus
from k9_aif_abb.k9_core.messaging.base_queue import LocalQueue


class MessageFactory:
    """
    Messaging ABB Factory (Singleton)
    ---------------------------------
    Creates or reuses a configured event bus instance from config.yaml.

    Example config:
      messaging:
        backend: redpanda
        brokers:
          - 192.168.1.98:9092
        topic: acme-events
        group_id: acme-console
    """

    _singleton = None
    _lock = threading.Lock()

    # ------------------------------------------------------------------
    # Create or reuse
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, config: Dict[str, Any], monitor: Any = None):
        """Create or reuse the singleton MessageBus."""
        if cls._singleton:
            return cls._singleton

        logger = logging.getLogger("MessageFactory")

        try:
            mcfg = config.get("messaging", {}) if isinstance(config, dict) else {}
            backend = str(mcfg.get("backend", "local")).lower()
            topic = mcfg.get("topic", "k9aif-events")
            group_id = mcfg.get("group_id", "k9aif-core")
            auto_create = bool(mcfg.get("auto_create", True))

            if backend in ("redpanda", "kafka"):
                brokers = mcfg.get("brokers", [])
                broker_url = brokers[0] if brokers else mcfg.get("broker_url", "localhost:9092")

                bus = K9EventBus(
                    backend=backend,
                    broker_url=broker_url,
                    topic=topic,
                    group_id=group_id,
                    auto_create=auto_create,
                    monitor=monitor,
                )

                with cls._lock:
                    cls._singleton = bus
                logger.info(f"[MessageFactory] [OK] Connected to {backend.capitalize()} at {broker_url}")
                return cls._singleton

            # ------------------------------------------------------------------
            # LocalQueue fallback (if no Kafka/Redpanda)
            # ------------------------------------------------------------------
            class _LocalBusAdapter:
                def __init__(self, q: LocalQueue):
                    self._q = q
                    self.topic = topic

                def publish(self, event: dict):
                    payload_bytes = len(json.dumps(event).encode("utf-8"))
                    print(f"[LocalBusAdapter] [INFO] Published local event ({payload_bytes/1024:.2f} KB)")
                    self._q.send(event.get("task_id", ""), event)

                def subscribe(self, callback, *, from_beginning: bool = False, group_id=None):
                    import time, threading

                    def _loop():
                        while True:
                            msg = self._q.receive()
                            if msg:
                                callback(msg["payload"])
                            else:
                                time.sleep(0.05)

                    threading.Thread(target=_loop, daemon=True).start()

                def close(self):
                    return

            with cls._lock:
                cls._singleton = _LocalBusAdapter(LocalQueue(name="LocalQueue", monitor=monitor))
            logger.info("[MessageFactory] [INFO] Using LocalQueue fallback (no Kafka/Redpanda backend found)")
            return cls._singleton

        except Exception as e:
            logger.error(f"[MessageFactory] [ERROR] Initialization failed: {e}", exc_info=True)
            with cls._lock:
                cls._singleton = LocalQueue(name="FallbackLocalQueue", monitor=monitor)
            return cls._singleton

    # ------------------------------------------------------------------
    # Unified publish (for all backends)
    # ------------------------------------------------------------------
    @classmethod
    def publish(cls, event: Dict[str, Any]):
        """Publish a JSON event to Kafka/Redpanda or LocalQueue."""
        try:
            if not cls._singleton:
                raise RuntimeError("MessageFactory not initialized; call create(config) first.")

            topic = event.get("topic", getattr(cls._singleton, "topic", "k9aif-events"))
            payload = json.dumps(event).encode("utf-8")

            # [OK] Kafka / Redpanda bus
            if hasattr(cls._singleton, "producer"):
                producer = cls._singleton.producer
                if producer:
                    producer.produce(topic=topic, value=payload)
                    producer.flush(0.5)
                    print(f"[MessageFactory] [INFO] Event sent -> {topic}")
                    return

            # [OK] Local bus fallback
            if hasattr(cls._singleton, "publish"):
                cls._singleton.publish(event)
                print(f"[MessageFactory] [INFO] Event queued locally -> {topic}")
                return

            print(f"[MessageFactory] [WARN] No active producer found for topic {topic}")

        except Exception as e:
            print(f"[MessageFactory] [ERROR] Publish error: {e}")

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------
    @classmethod
    def get_global(cls):
        if cls._singleton:
            return cls._singleton
        raise RuntimeError("MessageFactory has no active MessageBus. Call create() first.")

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._singleton is not None

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._singleton = None
        logging.getLogger("MessageFactory").info("MessageFactory reset complete.")