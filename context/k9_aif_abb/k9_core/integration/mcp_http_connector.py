# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import datetime
from typing import Any, Dict
import httpx

from k9_aif_abb.k9_core.integration.base_connector import BaseConnector


class MCPHttpConnector(BaseConnector):
    """
    SBB: MCP client connector over HTTP(S).
    Sends plain HTTP requests to an MCP server endpoint.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "mcp-http")
        self.base_url = config.get("kwargs", {}).get("base_url", "http://localhost:8000")
        self.api_key = config.get("kwargs", {}).get("api_key")  # optional

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        super().log(f"{ts} | {self.__class__.__name__:<18} | {msg}", level=level)

    async def connect(self):
        # No persistent connection needed for HTTP
        self.log(f"Using MCP HTTP server at {self.base_url}")

    async def list_tools(self) -> Dict[str, Any]:
        """Optional: fetch tool list if server supports it."""
        url = f"{self.base_url}/tools"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a named tool on the MCP server.

        Sends a POST to ``{base_url}/tools/call`` with the standard MCP envelope::

            {"name": tool_name, "arguments": {...}}

        Any MCP-compatible server (Brave Search, Tavily, Docling, custom) can
        be targeted by setting ``base_url`` in config — no code changes needed.
        """
        url = f"{self.base_url}/tools/call"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"name": tool_name, "arguments": arguments},
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def close(self):
        self.log("Closing MCP HTTP connector (no persistent session)")