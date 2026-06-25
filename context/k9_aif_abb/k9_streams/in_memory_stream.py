# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""InMemoryEventFabric + InMemoryContextWindow — local testing SBBs, no Kafka needed."""

import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from k9_aif_abb.k9_core.streams.base_context_window import BaseContextWindow
from k9_aif_abb.k9_core.streams.base_event_fabric import BaseEventFabric
from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope


class InMemoryEventFabric(BaseEventFabric):
    """
    In-memory event fabric SBB for local development and testing.
    No Kafka, Confluent, or external services required.

    Callbacks are invoked synchronously on publish(). Thread-safe.
    Swap for KafkaEventFabric in production via config — no code changes needed.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def publish(self, envelope: EventEnvelope, topic: str) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(topic, []))
        for cb in callbacks:
            cb(envelope)

    def subscribe(self, topic: str, callback: Callable[[EventEnvelope], None]) -> None:
        with self._lock:
            self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str) -> None:
        with self._lock:
            self._subscribers.pop(topic, None)

    def close(self) -> None:
        with self._lock:
            self._subscribers.clear()


class InMemoryContextWindow(BaseContextWindow):
    """
    In-memory sliding context window SBB for local development and testing.

    Retains up to max_events envelopes; oldest evicted when full.
    No external dependencies. Swap for RedisContextWindow in distributed deployments.

    YAML config::

        streams:
          window:
            max_events: 500
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        window_cfg = self.config.get("streams", {}).get("window", {})
        self._max_events: int = int(window_cfg.get("max_events", 500))
        self._events: List[EventEnvelope] = []
        self._lock = threading.Lock()

    def add(self, envelope: EventEnvelope) -> None:
        with self._lock:
            self._events.append(envelope)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    def query(
        self,
        event_type:     Optional[str]      = None,
        source_system:  Optional[str]      = None,
        since:          Optional[datetime] = None,
        correlation_id: Optional[str]      = None,
        limit:          Optional[int]      = None,
    ) -> List[EventEnvelope]:
        with self._lock:
            results = list(self._events)
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if source_system:
            results = [e for e in results if e.source_system == source_system]
        if since:
            results = [e for e in results if e.timestamp >= since]
        if correlation_id:
            results = [e for e in results if e.correlation_id == correlation_id]
        if limit:
            results = results[-limit:]
        return results

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            events = list(self._events)
        if not events:
            return {"total_events": 0, "sources": [], "event_types": []}
        return {
            "total_events": len(events),
            "sources":      sorted({e.source_system for e in events}),
            "event_types":  sorted({e.event_type for e in events}),
            "oldest":       events[0].timestamp.isoformat(),
            "newest":       events[-1].timestamp.isoformat(),
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
