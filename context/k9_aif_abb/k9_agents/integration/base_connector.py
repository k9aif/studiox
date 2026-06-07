# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/integration/base_connector.py

from abc import abstractmethod
from typing import Any, Dict
from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseConnector(BaseComponent):
    """
    K9-AIF BaseConnector
    --------------------
    ABB-level base for all integration connectors.
    Inherits BaseComponent to gain unified logging,
    telemetry, and governance hooks.
    """

    layer = "Integration ABB"

    def __init__(self, config: Dict[str, Any] | None = None, name: str | None = None):
        super().__init__(config=config, name=name or self.__class__.__name__)
        self.log(f"[{self.layer}] Initialized connector '{self.name}'", "DEBUG")

    def connect(self) -> bool:
        """Establish a connection if applicable."""
        self.log(f"[{self.layer}] connect() called (default no-op)", "DEBUG")
        return True

    def close(self) -> None:
        """Close or cleanup connection resources."""
        self.log(f"[{self.layer}] close() called (default no-op)", "DEBUG")

    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke external system and return normalized response."""
        raise NotImplementedError