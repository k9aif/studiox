# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import asyncio
import datetime
import json
import logging
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.integration.base_connector import BaseConnector
import mcp.types as mcp_types  # for LATEST_PROTOCOL_VERSION

class MCPClientConnector(BaseConnector):
    """
    SBB: Concrete MCP client connector (pure stdio).
    Spawns an MCP server process and speaks MCP JSON-RPC over stdio.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = config
        self.name = config.get("name", "mcp-connector")
        self.command = config.get("command", [])

        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.msg_id = 0

        self.logger = logging.getLogger(self.__class__.__name__)

    # ---------------- logging ----------------
    def _log(self, msg: str, level: str = "INFO"):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {level:<5} | {self.__class__.__name__:<20} | {msg}"
        if level == "ERROR":
            self.logger.error(line)
        elif level == "WARN":
            self.logger.warning(line)
        elif level == "DEBUG":
            self.logger.debug(line)
        else:
            self.logger.info(line)

    # ---------------- wire helpers ----------------
    async def _send(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and await the result."""
        self.msg_id += 1
        message = {"jsonrpc": "2.0", "id": self.msg_id, "method": method, "params": params}
        payload = json.dumps(message) + "\n"

        self._log(f"--> {payload.strip()}", "DEBUG")
        assert self.writer is not None
        self.writer.write(payload.encode())
        await self.writer.drain()

        assert self.reader is not None
        line = await self.reader.readline()
        if not line:
            raise RuntimeError("MCP server closed the connection")

        self._log(f"<-- {line.decode().strip()}", "DEBUG")
        response = json.loads(line.decode())
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        return response.get("result", {})

    async def _notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification (no id)."""
        message = {"jsonrpc": "2.0", "method": method}
        if params:
            message["params"] = params
        payload = json.dumps(message) + "\n"

        self._log(f"--> {payload.strip()}", "DEBUG")
        assert self.writer is not None
        self.writer.write(payload.encode())
        await self.writer.drain()

    async def _initialize(self) -> None:
        """MCP handshake: initialize + notifications/initialized."""
        protocol = mcp_types.LATEST_PROTOCOL_VERSION  # authoritative version string
        init_params = {
            "protocolVersion": protocol,
            "capabilities": {
                "sampling": {},           # allowed but no-op for us
                "roots": {"listChanged": True},
                "experimental": None
            },
            "clientInfo": {"name": "k9-aif", "version": "0.1.0"},
        }
        self._log(f"Initializing MCP session (protocol={protocol})", "INFO")
        await self._send("initialize", init_params)
        await self._notify("notifications/initialized", {})
        self._log("MCP session initialized", "INFO")

    # ---------------- public API ----------------
    async def connect(self):
        """Start process, open pipes, perform MCP handshake."""
        if self.process:
            return

        self._log(f"Spawning MCP server: {self.command}", "INFO")
        self.process = await asyncio.create_subprocess_exec(
            *self.command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
        )
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        self._log("MCP process started", "INFO")

        # Required MCP handshake (fixes 'Received request before initialization was complete')
        await self._initialize()

    async def list_tools(self) -> Dict[str, Any]:
        return await self._send("tools/list", {})

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # After handshake, this matches the SDK's CallToolRequestParams schema.
        # name: str, arguments: dict | None
        return await self._send("tools/call", {"name": tool_name, "arguments": arguments})

    async def close(self):
        if self.process:
            self._log("Terminating MCP server", "INFO")
            self.process.terminate()
            await self.process.wait()
            self.process = None