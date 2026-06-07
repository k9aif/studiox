# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/base_provider_adapter.py

from abc import ABC, abstractmethod
from typing import Any, Dict
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class BaseProviderAdapter(ABC):
    """
    K9-AIF Inference ABB — BaseProviderAdapter
    -------------------------------------------
    Abstract contract for all LLM provider adapters.

    LLMFactory resolves an adapter from ProviderAdapterRegistry and calls
    create_llm() — it never constructs provider-specific objects directly.

    To add a new provider: extend BaseProviderAdapter, implement both
    provider_name and create_llm(), then register with:
        ProviderAdapterRegistry.register("myprovider", MyProviderAdapter)
    No changes to LLMFactory, agents, squads, or orchestrators are needed.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Registry key for this adapter (e.g. 'ollama', 'openai')."""
        raise NotImplementedError

    @abstractmethod
    def create_llm(
        self,
        model_name: str,
        factory_cfg: Dict[str, Any],
        extra_kwargs: Dict[str, Any],
    ) -> BaseLLM:
        """
        Construct and return a BaseLLM instance for this provider.

        Args:
            model_name:  The model identifier string (e.g. "gpt-4o-mini").
            factory_cfg: The full inference.llm_factory config dict.
            extra_kwargs: Optional kwargs forwarded from the model config
                          (e.g. temperature, max_tokens).
        """
        raise NotImplementedError
