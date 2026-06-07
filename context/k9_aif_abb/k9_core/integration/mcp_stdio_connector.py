# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import asyncio
import json
import datetime
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.integration.base_connector import BaseConnector


class MCPStdioConnector(BaseConnector):
    """
    SBB: MCP client connector over stdio.
    Spawns an MCP server process and communicates over stdin/stdout
    using JSON-RPC messages.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "mcp-stdio")
        self.command = config.get("command", [])

        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.msg_id = 0

    async def connect(self):
        if self.process:
            return
        self.logger.info(f"Spawning MCP server: {self.command}")
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        self.logger.info("MCP process started")

    async def _send(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.msg_id += 1
        message = {"jsonrpc": "2.0", "id": self.msg_id, "method": method, "params": params}
        payload = json.dumps(message) + "\n"
        self.logger.debug(f"Sending MCP request: {payload.strip()}")

        self.writer.write(payload.encode())
        await self.writer.drain()

        line = await self.reader.readline()
        if not line:
            raise RuntimeError("MCP server closed the connection")

        response = json.loads(line.decode())
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        return response.get("result", {})

    async def list_tools(self) -> Dict[str, Any]:
        return await self._send("tools/list", {})

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self._send("tools/call", {"name": tool_name, "arguments": arguments})

    async def close(self):
        if self.process:
            self.logger.info("Terminating MCP server")
            self.process.terminate()
            await self.process.wait()
            self.process = None