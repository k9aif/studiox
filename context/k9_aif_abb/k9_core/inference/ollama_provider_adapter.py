# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/ollama_provider_adapter.py

from typing import Any, Dict

from k9_aif_abb.k9_core.inference.base_provider_adapter import BaseProviderAdapter
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class OllamaProviderAdapter(BaseProviderAdapter):
    """
    K9-AIF Inference SBB — OllamaProviderAdapter
    ---------------------------------------------
    Creates an OllamaLLM from the factory config.
    Preserves all existing Ollama behaviour — this is a thin wrapper
    that moves construction logic out of LLMFactory.

    Config keys read from inference.llm_factory:
        base_url  — Ollama server URL (default: http://localhost:11434)
    """

    @property
    def provider_name(self) -> str:
        return "ollama"

    def create_llm(
        self,
        model_name: str,
        factory_cfg: Dict[str, Any],
        extra_kwargs: Dict[str, Any],
    ) -> BaseLLM:
        from k9_aif_abb.k9_core.inference.ollama_llm import OllamaLLM

        base_url = factory_cfg.get("base_url", "http://localhost:11434")
        return OllamaLLM(host=base_url, model=model_name, **extra_kwargs)
