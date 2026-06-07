# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
WebSearchAgent — MCP-backed web search ABB.

Delegates all HTTP communication to MCPHttpConnector.  The MCP server URL,
tool name, and result limit are fully config-driven — any MCP-compatible
search server (Brave Search, Tavily, DuckDuckGo) can be substituted without
changing this class.

Config keys (under ``mcp.web_search``):
    base_url    : str   — MCP server base URL (required)
    api_key     : str   — optional bearer token
    tool_name   : str   — tool name to call on the server (default: web_search)
    max_results : int   — maximum results to return (default: 5)

Expected payload keys:
    query : str — the search query (required)

Example config.yaml entry:
    mcp:
      web_search:
        base_url: "http://localhost:3000"
        api_key: null
        tool_name: web_search
        max_results: 5
"""

import asyncio
import concurrent.futures
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.agent.base_mcp_agent import BaseMCPAgent
from k9_aif_abb.k9_core.integration.mcp_http_connector import MCPHttpConnector


class WebSearchAgent(BaseMCPAgent):
    """
    ABB: agent that performs web search via an MCP-compatible search server.

    Extends BaseMCPAgent — the MCP contract (connect / send_request / close)
    is satisfied by the internally managed MCPHttpConnector instance.
    Callers use the standard BaseAgent interface: ``execute(payload) -> dict``.
    """

    layer = "WebSearchAgent ABB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config=config or {}, monitor=monitor)
        mcp_cfg = (self.config.get("mcp") or {}).get("web_search") or {}
        self._connector = MCPHttpConnector({
            "name":   "mcp-web-search",
            "kwargs": {
                "base_url": mcp_cfg.get("base_url", "http://localhost:3000"),
                "api_key":  mcp_cfg.get("api_key"),
            },
        })
        self._tool_name   = mcp_cfg.get("tool_name", "web_search")
        self._max_results = int(mcp_cfg.get("max_results", 5))

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = (payload.get("query") or "").strip()
        if not query:
            self.logger.warning("[%s] No query in payload", self.layer)
            return {"agent": self.layer, "query": "", "results": [], "error": "missing query"}

        self.logger.info("[%s] Searching: %s", self.layer, query)

        raw     = self._run_async(self._search(query))
        results = self._parse(raw)

        self.publish_event({
            "type":         "WebSearchCompleted",
            "agent":        self.layer,
            "query":        query,
            "result_count": len(results),
        })

        return {
            "agent":   self.layer,
            "query":   query,
            "results": results,
        }

    # ------------------------------------------------------------------
    # BaseMCPAgent contract — delegated to MCPHttpConnector
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        self._run_async(self._connector.connect())
        return True

    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_async(self._connector.call_tool(
            request.get("tool", self._tool_name),
            request.get("arguments", {}),
        ))

    def close(self) -> None:
        self._run_async(self._connector.close())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _search(self, query: str) -> Any:
        await self._connector.connect()
        try:
            return await self._connector.call_tool(
                self._tool_name,
                {"query": query, "max_results": self._max_results},
            )
        finally:
            await self._connector.close()

    def _parse(self, raw: Any) -> List[Dict[str, Any]]:
        """Normalise MCP server response to a flat list of result dicts."""
        if isinstance(raw, list):
            return raw[:self._max_results]
        if isinstance(raw, dict):
            return raw.get("results", [raw])[:self._max_results]
        return []

    @staticmethod
    def _run_async(coro) -> Any:
        """Run a coroutine from a synchronous context."""
        try:
            asyncio.get_running_loop()
            # Already inside a running loop (e.g. FastAPI) — run in a thread
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            return asyncio.run(coro)
