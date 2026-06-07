# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

class BaseMCPAgent(BaseAgent, ABC):
    """Abstract base class for Model Context Protocol (MCP) agents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the MCP server."""
        ...

    @abstractmethod
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close connection to MCP server."""
        ...