# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/messaging/base_message_agent.py

from abc import ABC, abstractmethod
import logging
from typing import Optional
from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseMessageAgent(BaseComponent, ABC):
    """
    K9-AIF Messaging ABB - BaseMessageAgent
    ---------------------------------------
    Abstract base for all messaging and queue agents (Kafka, SQS, RabbitMQ, etc.).

    Responsibilities:
    - Define lifecycle for connecting and closing message channels.
    - Provide unified telemetry via BaseComponent.
    - Offer layer-aware logging visible in the live K9-AIF console.
    """

    layer = "Messaging ABB"

    def __init__(self, name: str = "BaseMessageAgent", monitor=None):
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(message, level)
        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

    @abstractmethod
    async def connect(self):
        """Connect to the messaging backend (to be implemented by subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        """Close the messaging connection (to be implemented by subclass)."""
        raise NotImplementedError