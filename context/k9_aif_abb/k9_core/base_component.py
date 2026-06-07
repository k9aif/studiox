# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/base_component.py

import asyncio
import logging
import time
from typing import Dict, Any, Optional


class BaseComponent:
    """
    K9-AIF ABB - BaseComponent
    --------------------------
    Common foundation for all ABB and SBB components.
    Provides unified logging, monitoring, and governed event publishing via the K9-AIF Message Bus.
    """

    def __init__(
        self,
        monitor=None,
        message_bus=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.monitor = monitor
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        self.message_bus = message_bus

        # [INFO] Lazy import to avoid circular dependency with factories/persistence
        if not self.message_bus and "messaging" in self.config:
            try:
                from k9_aif_abb.k9_factories.message_factory import MessageFactory
                self.message_bus = MessageFactory.create(self.config)
                self.logger.info(
                    f"[{self.__class__.__name__}] MessageBus initialized from config.yaml"
                )
            except Exception as e:
                self.logger.warning(f" MessageBus initialization failed: {e}")
                self.message_bus = None
        else:
            self.logger.debug(
                f"[{self.__class__.__name__}] No messaging config found or bus injected."
            )

    async def log(self, message: str, level: str = "INFO", **kwargs):
        """
        Unified async log:
          1. Logs to standard Python logger
          2. Emits to monitor (if available)
          3. Publishes structured event to the configured MessageBus
        """
        formatted = f"[{self.__class__.__name__}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

        # Emit to live monitor / UI console
        if self.monitor:
            try:
                await self.monitor.emit(message, level)
            except Exception as e:
                self.logger.debug(f"Monitor emit failed: {e}")

        # Structured publish to the message bus (if configured)
        if self.message_bus:
            event = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "component": self.__class__.__name__,
                "level": level,
                "message": message,
                "extra": kwargs,
                "topic": self.config.get("messaging", {}).get("topic", "k9aif-events"),
            }
            try:
                if asyncio.iscoroutinefunction(self.message_bus.publish):
                    await self.message_bus.publish(event)
                else:
                    self.message_bus.publish(event)
            except Exception as e:
                self.logger.debug(f"MessageBus publish failed: {e}")