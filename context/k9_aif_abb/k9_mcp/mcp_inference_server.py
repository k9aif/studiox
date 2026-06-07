# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_mcp/servers/mcp_inference_server.py

from typing import Dict, Any
from k9_aif_abb.k9_mcp.servers.base_mcp_server import BaseMCPServer
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class MCPInferenceServer(BaseMCPServer):
    """
    ABB: Bridges the Inference ABB to external MCP clients.
    Handles prompt-based requests and delegates to a configured LLM.
    """

    layer = "MCP ABB"

    def __init__(self, llm: BaseLLM, name: str = "MCPInferenceServer", monitor=None):
        super().__init__(name=name, monitor=monitor)
        self.llm = llm

    async def handle_request(self, request: Dict[str, Any], ctx=None) -> Dict[str, Any]:
        prompt = request.get("prompt", "")
        await self.log(f"Received MCP inference request: {prompt}", level="INFO")

        result = self.llm.generate(prompt)
        await self.log("Returning LLM response", level="DEBUG")

        return {"status": "ok", "response": result}