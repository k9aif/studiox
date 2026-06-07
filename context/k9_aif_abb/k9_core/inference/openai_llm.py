# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/openai_llm.py

import logging
from typing import Any, Optional
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class OpenAILLM(BaseLLM):
    """
    K9-AIF Inference SBB - OpenAILLM
    ----------------------------------
    OpenAI-compatible LLM backend. Works with:
      - OpenAI API  (base_url=None, api_key=OPENAI_API_KEY)
      - Grok / xAI  (base_url="https://api.x.ai/v1", api_key=GROK_API_KEY)
      - Any OpenAI-compatible endpoint

    Drop-in replacement for OllamaLLM — same generate() contract.
    Provider is selected via backend: openai in config.yaml.
    """

    layer = "Inference SBB"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        monitor: Optional[Any] = None,
        **kwargs: Any,
    ):
        super().__init__(name="OpenAILLM", monitor=monitor)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is required for OpenAILLM. "
                "Run: pip install openai>=1.0"
            ) from exc

        client_kwargs: dict = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = AsyncOpenAI(**client_kwargs)
        self.logger = logging.getLogger("OpenAILLM")

    async def generate(self, prompt: str) -> str:
        await self.log(f"Sending inference request to OpenAI ({self.model})", "DEBUG")
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            text = response.choices[0].message.content or ""
            text = text.strip()
            await self.log(f"OpenAI responded ({len(text)} chars)", "INFO")
            return text or "[WARN] No response from model."
        except Exception as e:
            msg = f"OpenAI request failed: {e}"
            await self.log(msg, "ERROR")
            return f"[WARN] OpenAI call failed: {e}"
