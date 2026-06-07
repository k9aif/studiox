# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class BaseIoTAgent(BaseAgent, ABC):
    """ABB: Abstract base class for IoT communication agents.
    Provides sync + async contracts for IoT operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})

    # -------------------
    # Sync API
    # -------------------
    @abstractmethod
    def connect(self) -> bool:
        """Connect to IoT broker/device (sync)."""
        ...

    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to an IoT topic (sync)."""
        ...

    @abstractmethod
    def subscribe(self, topic: str, callback) -> None:
        """Subscribe to a topic and handle messages via callback (sync)."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from IoT broker/device (sync)."""
        ...

    # -------------------
    # Async API
    # -------------------
    @abstractmethod
    async def connect_async(self) -> bool:
        """Connect to IoT broker/device (async)."""
        ...

    @abstractmethod
    async def publish_async(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to an IoT topic (async)."""
        ...

    @abstractmethod
    async def subscribe_async(self, topic: str, callback) -> None:
        """Subscribe to a topic and handle messages via callback (async)."""
        ...

    @abstractmethod
    async def disconnect_async(self) -> None:
        """Disconnect from IoT broker/device (async)."""
        ...