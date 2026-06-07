# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
MCP Client Agent (ABB)

This agent represents the architectural contract for interacting with
Model Context Protocol (MCP) servers.

Concrete implementations should extend this class to connect to
external MCP-compatible tools and services.
"""

from k9_aif_abb.k9_core.agent.base_mcp_agent import BaseMCPAgent


class MCPClientAgent(BaseMCPAgent):
    """
    Architecture Building Block (ABB)

    Defines the interface for agents that communicate with MCP servers.
    """

    def connect(self):
        raise NotImplementedError("MCP client connection not implemented yet.")

    def send_request(self, payload):
        raise NotImplementedError("MCP client request handling not implemented yet.")
