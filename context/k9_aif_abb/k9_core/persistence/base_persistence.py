# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/persistence/base_persistence.py

import threading
import logging
import time
import asyncio
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod

from k9_aif_abb.k9_core.base_component import BaseComponent


class BasePersistence(BaseComponent, ABC):
    """
    K9-AIF Persistence ABB - BasePersistence
    ----------------------------------------
    Abstract base class for persistence backends that store agent/orchestrator state.

    Responsibilities:
      - Define standard CRUD contract for persistent or transient state.
      - Integrate with BaseComponent for unified logging and monitoring.
      - Optionally emit structured telemetry to the global MessageBus (Redpanda/Kafka).
    """

    layer = "Persistence ABB"

    def __init__(self, name: str = "BasePersistence", monitor=None,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(monitor=monitor)
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(self.name)

        # ------------------------------------------------------------------
        # Lazy import to avoid circular dependency with factories
        # ------------------------------------------------------------------
        try:
            from k9_aif_abb.k9_factories.message_factory import MessageFactory
            self.message_bus = MessageFactory.get_global() or MessageFactory.create(self.config)
            if self.message_bus:
                self.logger.debug(f"[{self.name}] Attached global MessageBus")
        except Exception as e:
            self.logger.debug(f"[{self.name}] MessageBus unavailable: {e}")
            self.message_bus = None

    # ------------------------------------------------------------------
    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async/sync log; writes to Python logger, monitor, and MessageBus."""
        try:
            level = level.upper()
            formatted = f"[{self.layer}:{self.name}] {message}"
            getattr(self.logger, level.lower(), self.logger.info)(formatted)

            # Forward to BaseComponent's log if available
            if hasattr(super(), "log"):
                await super().log(message, level)

            # Emit structured event if bus exists
            if self.message_bus:
                event = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "component": self.name,
                    "layer": self.layer,
                    "level": level,
                    "message": message,
                    "topic": self.config.get("messaging", {}).get("topic", "k9aif-events"),
                }

                if asyncio.iscoroutinefunction(self.message_bus.publish):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.message_bus.publish(event))
                    else:
                        await self.message_bus.publish(event)
                else:
                    self.message_bus.publish(event)

        except Exception as e:
            self.logger.debug(f"[{self.name}] Log error: {e}")

    # ------------------------------------------------------------------
    # Abstract CRUD contract
    # ------------------------------------------------------------------
    @abstractmethod
    def save_state(self, key: str, state: Dict[str, Any]) -> None:
        """Persist a state dictionary under a unique key."""
        ...

    @abstractmethod
    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve persisted state by key, or None if missing."""
        ...

    @abstractmethod
    def update_state(self, key: str, state: Dict[str, Any]) -> None:
        """Update a persisted state record."""
        ...

    @abstractmethod
    def delete_state(self, key: str) -> None:
        """Delete a persisted record by key."""
        ...


# ======================================================================
# In-Memory Persistence SBB Implementation
# ======================================================================
class MemoryPersistence(BasePersistence):
    """SBB: In-memory dictionary persistence (non-durable, thread-safe)."""

    def __init__(self, monitor=None, config=None):
        super().__init__(name="MemoryPersistence", monitor=monitor, config=config)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def save_state(self, key: str, state: Dict[str, Any]) -> None:
        with self._lock:
            self._store[key] = state
        self.logger.info(f"[{self.layer}:{self.name}] Saved state for key={key}")
        if self.monitor:
            self.monitor.emit_metric("memory_persistence_saves", 1, {"key": key})

    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._store.get(key)

    def update_state(self, key: str, state: Dict[str, Any]) -> None:
        with self._lock:
            if key in self._store:
                self._store[key].update(state)
            else:
                self._store[key] = state
        self.logger.info(f"[{self.layer}:{self.name}] Updated state for key={key}")
        if self.monitor:
            self.monitor.emit_metric("memory_persistence_updates", 1, {"key": key})

    def delete_state(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)
        self.logger.info(f"[{self.layer}:{self.name}] Deleted state for key={key}")
        if self.monitor:
            self.monitor.emit_metric("memory_persistence_deletes", 1, {"key": key})