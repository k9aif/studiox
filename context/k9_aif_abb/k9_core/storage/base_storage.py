# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/storage/base_storage.py

from abc import ABC, abstractmethod
from typing import Any, Optional
import logging

from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseStorage(BaseComponent, ABC):
    """
    K9-AIF Storage ABB - BaseStorage
    --------------------------------
    Abstract base class for all storage backends (local or cloud-based).

    Responsibilities:
    - Define a standard CRUD interface for storing and retrieving binary or structured data.
    - Integrate with BaseComponent for telemetry and monitor streaming.
    - Provide layer-aware console output for storage events.
    """

    layer = "Storage ABB"

    def __init__(self, name: str = "BaseStorage", monitor=None):
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(message, level)
        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

    # ------------------------------------------------------------------
    # Abstract CRUD contract
    # ------------------------------------------------------------------
    @abstractmethod
    def save(self, key: str, data: Any) -> None:
        """Persist data at the given key."""
        raise NotImplementedError

    @abstractmethod
    def load(self, key: str) -> Any:
        """Retrieve data for the given key."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove data for the given key."""
        raise NotImplementedError

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """List available keys, optionally filtered by prefix."""
        raise NotImplementedError