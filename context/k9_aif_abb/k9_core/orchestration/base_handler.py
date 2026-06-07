# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/orchestration/base_handler.py
from __future__ import annotations

from typing import Dict, Any, Optional
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
import asyncio


class Handler:
    """
    K9-AIF Orchestration ABB - Handler
    ----------------------------------
    Generic handler for Chain of Responsibility (CoR) patterns.
    Wraps an agent (or other handler-capable object) and delegates requests.
    """

    layer = "Orchestration ABB"

    def __init__(self, agent: BaseAgent, successor: Handler | None = None):
        self.agent = agent
        self.successor = successor

    # -------------------------
    # Sync entrypoint
    # -------------------------
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the current agent and forward to successor."""
        if hasattr(self.agent, "logger"):
            self.agent.logger.debug(f"[{self.layer}] {self.agent.__class__.__name__} handling request")

        result = self.agent.execute(request)
        if self.successor:
            return self.successor.handle(result)
        return result

    # -------------------------
    # Async entrypoint
    # -------------------------
    async def handle_async(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Async variant of handle() for coroutine-compatible agents."""
        if hasattr(self.agent, "log"):
            # Use unified telemetry pipeline if available
            await self.agent.log(f"{self.agent.__class__.__name__} handling request", level="DEBUG")
        elif hasattr(self.agent, "logger"):
            self.agent.logger.debug(f"[{self.layer}] {self.agent.__class__.__name__} handling request")

        # Prefer native async execute
        if hasattr(self.agent, "execute_async"):
            result = await self.agent.execute_async(request)
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.agent.execute, request)

        if self.successor:
            return await self.successor.handle_async(result)
        return result


class AgentHandler(Handler):
    """
    Specialization: explicitly wraps a K9-AIF Agent as a CoR handler.
    Adds standardized orchestration-layer telemetry.
    """

    layer = "Orchestration ABB"

    def __init__(self, agent: BaseAgent, successor: Optional[Handler] = None):
        super().__init__(agent, successor)

    # Sync
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if hasattr(self.agent, "logger"):
            self.agent.logger.info(f"[{self.layer}] [CoR] {self.agent.__class__.__name__} handling request")
        return super().handle(request)

    # Async
    async def handle_async(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if hasattr(self.agent, "log"):
            await self.agent.log(f"[CoR] {self.agent.__class__.__name__} handling request")
        elif hasattr(self.agent, "logger"):
            self.agent.logger.info(f"[{self.layer}] [CoR] {self.agent.__class__.__name__} handling request")
        return await super().handle_async(request)