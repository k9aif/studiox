# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/openai_provider_adapter.py

import os
from typing import Any, Dict

from k9_aif_abb.k9_core.inference.base_provider_adapter import BaseProviderAdapter
from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class OpenAIProviderAdapter(BaseProviderAdapter):
    """
    K9-AIF Inference SBB — OpenAIProviderAdapter
    ---------------------------------------------
    Creates an OpenAILLM for any OpenAI-compatible endpoint.
    Covers:
        - OpenAI API        (backend: openai,             api_key_env: OPENAI_API_KEY)
        - Grok / xAI        (backend: openai-compatible,  api_key_env: GROK_API_KEY,
                             base_url: https://api.x.ai/v1)
        - Any future OpenAI-compatible endpoint

    API key resolution order:
        1. api_key_env: ENV_VAR_NAME  — preferred; key stays out of config
        2. api_key: ${ENV_VAR_NAME}   — legacy; expanded via os.path.expandvars
        3. Environment variable OPENAI_API_KEY — last-resort fallback

    API keys must NEVER be stored as raw values in config.yaml.
    If the required env var is not set, fail clearly with an actionable error.
    """

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    def create_llm(
        self,
        model_name: str,
        factory_cfg: Dict[str, Any],
        extra_kwargs: Dict[str, Any],
    ) -> BaseLLM:
        from k9_aif_abb.k9_core.inference.openai_llm import OpenAILLM

        api_key = self._resolve_api_key(factory_cfg)
        base_url = self._resolve_base_url(factory_cfg)

        return OpenAILLM(
            api_key=api_key,
            model=model_name,
            base_url=base_url,
            **extra_kwargs,
        )

    # ── private helpers ────────────────────────────────────────────────

    def _resolve_api_key(self, factory_cfg: Dict[str, Any]) -> str:
        # 1. Explicit env var name in config (preferred)
        env_var = factory_cfg.get("api_key_env", "").strip()
        if env_var:
            value = os.environ.get(env_var, "")
            if not value:
                raise EnvironmentError(
                    f"Environment variable '{env_var}' (api_key_env) is not set. "
                    f"Add it to your .env file before running."
                )
            return value

        # 2. api_key with ${VAR} placeholder (legacy / convenience)
        raw_key = factory_cfg.get("api_key", "").strip()
        if raw_key:
            resolved = os.path.expandvars(raw_key)
            if resolved and not resolved.startswith("$"):
                return resolved

        # 3. Implicit OPENAI_API_KEY fallback
        fallback = os.environ.get("OPENAI_API_KEY", "")
        if fallback:
            return fallback

        raise EnvironmentError(
            "OpenAI-compatible backend requires an API key. "
            "Set api_key_env: OPENAI_API_KEY (or GROK_API_KEY) in config.yaml "
            "and export the variable in your .env file."
        )

    def _resolve_base_url(self, factory_cfg: Dict[str, Any]) -> str | None:
        raw = factory_cfg.get("base_url", "").strip()
        if not raw:
            return None
        resolved = os.path.expandvars(raw)
        return resolved if resolved else None
