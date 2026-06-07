# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_mcp/servers/base_mcp_server.py

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseMCPServer(BaseComponent, ABC):
    """
    K9-AIF MCP ABB - BaseMCPServer
    --------------------------------
    Abstract base class for all MCP protocol servers.
    Provides lifecycle and request handling contracts
    that concrete SBBs (e.g., WeatherMCPServer, EnrichmentMCPServer)
    will implement.

    Responsibilities:
    - Start and manage MCP server lifecycle.
    - Accept and dispatch MCP-formatted requests.
    - Run pre/post governance hooks and emit telemetry.
    """

    layer = "MCP ABB"

    def __init__(self, name: str = "BaseMCPServer", monitor: Optional[Any] = None):
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.log(f"{self.name} initialized (layer={self.layer})", "INFO")

    # ------------------------------------------------------
    # Abstract contract
    # ------------------------------------------------------
    @abstractmethod
    async def handle_request(self, request: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a single MCP request asynchronously."""
        raise NotImplementedError

    # ------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------
    def start(self) -> None:
        """Start the MCP server (override in SBB)."""
        self.log(f"{self.name} started", "INFO")

    def stop(self) -> None:
        """Stop the MCP server (override in SBB)."""
        self.log(f"{self.name} stopped", "INFO")