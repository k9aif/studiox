# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/messaging/base_queue.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import queue

# [INFO] Do NOT import BaseComponent at top - it causes circular import.
# We'll import it lazily inside the class.


class BaseQueue(ABC):
    """
    K9-AIF Messaging ABB - BaseQueue
    --------------------------------
    Abstract base class for message queue backends (SQS, Kafka, RabbitMQ, etc.).
    Defines send/receive/delete lifecycle for queue operations and
    provides optional telemetry if BaseComponent is available.
    """

    layer = "Messaging ABB"

    def __init__(self, name: str = "BaseQueue", monitor=None):
        # Lazy import to avoid circular dependency
        try:
            from k9_aif_abb.k9_core.base_component import BaseComponent
            if not isinstance(self, BaseComponent):
                # Dynamically attach logging capability if not already present
                self.logger = logging.getLogger(name)
        except ImportError:
            self.logger = logging.getLogger(name)

        self.name = name
        self.monitor = monitor
        self._q = queue.Queue()

    # --- Abstract contract ---
    @abstractmethod
    def send(self, task_id: str, payload: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, task_id: str) -> None:
        raise NotImplementedError


class LocalQueue(BaseQueue):
    """In-memory queue for local testing and async flow simulation."""

    def send(self, task_id: str, payload: Dict[str, Any]) -> None:
        self._q.put({"task_id": task_id, "payload": payload})
        self.logger.debug(f"[{self.layer}:{self.name}] Enqueued task {task_id}")

    def receive(self) -> Optional[Dict[str, Any]]:
        try:
            msg = self._q.get_nowait()
            self.logger.debug(f"[{self.layer}:{self.name}] Dequeued task {msg['task_id']}")
            return msg
        except queue.Empty:
            return None

    def delete(self, task_id: str) -> None:
        # LocalQueue does not persist messages - delete is a no-op
        self.logger.debug(f"[{self.layer}:{self.name}] Delete noop for {task_id}")