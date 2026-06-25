# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework
# File: k9_aif_abb/k9_core/inference/mock_provider_adapter.py
"""
MockProviderAdapter — returns deterministic responses without any network call.
Use provider: mock in config.yaml for testing and demos with no Ollama needed.
"""

from typing import Any, Dict

from k9_aif_abb.k9_core.inference.base_provider_adapter import BaseProviderAdapter
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class MockProviderAdapter(BaseProviderAdapter):
    """Provides MockLLM — no network, no Ollama, deterministic responses."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def create_llm(
        self,
        model_name: str,
        factory_cfg: Dict[str, Any],
        extra_kwargs: Dict[str, Any],
    ) -> BaseLLM:
        from k9_aif_abb.k9_core.inference.mock_llm import MockLLM
        return MockLLM()
