# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# K9-AIF - Async OllamaLLM (governed inference bridge)

import aiohttp
import traceback
import asyncio
from typing import Any, Optional
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class OllamaLLM(BaseLLM):
    """
    K9-AIF Inference SBB - Async OllamaLLM
    --------------------------------------
    - Asynchronous generation using aiohttp.
    - Fully compatible with ChatAgent (await self.llm.generate()).
    - Logs safely through BaseLLM.
    """

    layer = "Inference SBB"

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.1:latest",
        timeout: int = 120,
        monitor: Optional[Any] = None,
        **kwargs: Any,
    ):
        super().__init__(name="OllamaLLM", monitor=monitor)
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.kwargs = kwargs

    # ----------------------------------------------------------
    async def generate(self, prompt: str) -> str:
        await self.log(f"Sending inference request to Ollama ({self.model})", "DEBUG")
        url = f"{self.host}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as resp:
                    body = await resp.text()

                    if resp.status != 200:
                        msg = f"Ollama HTTP {resp.status} | model={self.model} | body={body}"
                        await self.log(msg, "WARNING")
                        return f"[WARN] {msg}"

                    data = await resp.json()
                    text = data.get("response", "").strip()
                    await self.log(f"Ollama responded ({len(text)} chars)", "INFO")
                    return text or "[WARN] No response from model."

        except Exception as e:
            msg = f"Ollama request failed: {e}"
            await self.log(msg, "ERROR")
            traceback.print_exc()
            return f"[WARN] Ollama connection failed: {e}"

    # ----------------------------------------------------------
    async def start(self):
        """Initialize aiohttp session (optional)."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        await self.log(f"OllamaLLM({self.model}) started", "INFO")

    async def stop(self):
        """Close aiohttp session (graceful shutdown)."""
        if self.session:
            await self.session.close()
            self.session = None
        await self.log(f"OllamaLLM({self.model}) stopped", "INFO")