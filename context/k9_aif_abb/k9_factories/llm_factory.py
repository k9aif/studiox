# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/llm_factory.py

import logging
import os
import traceback
import yaml
from typing import Dict, Any, Optional
from k9_aif_abb.k9_core.inference.ollama_llm import OllamaLLM


class LLMFactory:
    """
    K9-AIF Factory ABB - LLMFactory
    -------------------------------
    Unified model manager for configured LLM backends.

    Current implementation supports Ollama-backed model instances.
    Additional provider dispatch (for example watsonx.ai or other backends)
    can be added in future versions without changing the public factory pattern.

    Backward-compatible with older agents expecting:
      - LLMFactory.is_bootstrapped
      - LLMFactory._models
      - LLMFactory.get_model()
    """

    # ------------------------------------------------------------------
    # Internal state
    # ------------------------------------------------------------------
    _bootstrapped: bool = False
    _cfg: Dict[str, Any] = {}
    _instances: Dict[str, Any] = {}

    # Legacy compatibility (for AdvisorAgent, etc.)
    _models: Dict[str, Any] = {}
    _is_bootstrapped: bool = False  # internal flag for callable property

    # ------------------------------------------------------------------
    # Callable compatibility shim
    # ------------------------------------------------------------------
    @classmethod
    def is_bootstrapped(cls) -> bool:
        """Legacy callable compatibility (for old agents)."""
        return cls._bootstrapped or cls._is_bootstrapped

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    @classmethod
    def bootstrap(cls, config):
        """Initialize the LLM factory (supports ABB + SBB flattened configs)."""
        try:
            config = config or {}

            # Normalize structure for flattened SBB configs
            if "inference" not in config and "llm_factory" in config:
                print("[LLMFactory] [INFO] Normalizing flattened config -> nesting under inference.llm_factory")
                config = {"inference": {"llm_factory": config["llm_factory"]}}

            llm_cfg = config.get("inference", {}).get("llm_factory", {})
            if not llm_cfg:
                raise ValueError("[LLMFactory] [ERROR] Missing inference.llm_factory section in config")

            cls._cfg = config
            cls._bootstrapped = True
            cls._is_bootstrapped = True

            # Keep raw models config for backward compatibility
            cls._models = llm_cfg.get("models", {})

            # Store configuration attributes
            cls.backend = llm_cfg.get("backend", "ollama")
            cls.provider = llm_cfg.get("provider", "ollama")
            cls.base_url = llm_cfg.get("base_url", "")

            print(f"[LLMFactory] [INFO] Loaded models -> {cls._models}")
            print(f"[LLMFactory] [INFO] Base URL -> {cls.base_url}")
            print(f"[LLMFactory] [OK] Provider -> {cls.provider}")
            print(f"[LLMFactory] [OK] Bootstrap complete")

        except Exception as e:
            print(f"[LLMFactory] [ERROR] Bootstrap failed: {e}")
            traceback.print_exc()
            raise

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------
    @classmethod
    def get(cls, alias: Optional[str] = "general") -> OllamaLLM:
        """
        Return a cached or newly constructed OllamaLLM instance for the alias.

        Supports both:
          1) legacy string model config:
             models:
               general: llama3

          2) structured dict model config:
             models:
               general:
                 provider: ollama
                 model: llama3.2:1b
                 temperature: 0.2
                 max_tokens: 2048
        """
        alias = alias or "general"

        if alias in cls._instances:
            return cls._instances[alias]

        if not cls._bootstrapped:
            raise RuntimeError("LLMFactory.get() called before bootstrap().")

        log = logging.getLogger("LLMFactory")

        inf = (cls._cfg or {}).get("inference", {})
        fcfg = inf.get("llm_factory") or {}
        base_url = fcfg.get("base_url", "http://localhost:11434")
        model_cfg = (fcfg.get("models") or {}).get(alias)

        if not model_cfg:
            raise KeyError(
                f"LLM model alias '{alias}' is not configured under inference.llm_factory.models"
            )

        # Backward-compatible handling
        if isinstance(model_cfg, str):
            model_name = model_cfg
            extra_kwargs = {}

        elif isinstance(model_cfg, dict):
            model_name = model_cfg.get("model")
            if not model_name:
                raise KeyError(
                    f"LLM model alias '{alias}' is missing required key 'model'"
                )

            extra_kwargs = {
                "temperature": model_cfg.get("temperature"),
                "max_tokens": model_cfg.get("max_tokens"),
            }
            extra_kwargs = {k: v for k, v in extra_kwargs.items() if v is not None}

        else:
            raise TypeError(
                f"LLM model alias '{alias}' must be a string or dict, got {type(model_cfg).__name__}"
            )

        # Resolve backend — support both 'backend' and legacy 'provider' keys
        backend = (fcfg.get("backend") or fcfg.get("provider") or "ollama").lower()

        from k9_aif_abb.k9_core.inference.provider_registry import ProviderAdapterRegistry
        adapter = ProviderAdapterRegistry.resolve(backend)
        inst = adapter.create_llm(model_name, fcfg, extra_kwargs)
        cls._instances[alias] = inst
        log.info(f"LLM instance ready [{alias} -> {model_name}] (cached).")

        return inst

    # ------------------------------------------------------------------
    # Legacy accessor (for older agents)
    # ------------------------------------------------------------------
    @classmethod
    def get_model(cls, name: str = "general") -> Optional[str]:
        """Return model identifier by logical name (legacy use)."""
        if not cls.is_bootstrapped():
            logging.getLogger("LLMFactory").warning(
                "get_model() called before bootstrap"
            )

        model_cfg = cls._models.get(name)
        if isinstance(model_cfg, dict):
            return model_cfg.get("model")
        return model_cfg

    # ------------------------------------------------------------------
    # Reset (for tests or reloads)
    # ------------------------------------------------------------------
    @classmethod
    def reset(cls):
        """Clear all loaded models and reset bootstrap flag."""
        cls._instances.clear()
        cls._bootstrapped = False
        cls._is_bootstrapped = False
        cls._cfg = {}
        cls._models = {}
        logging.getLogger("LLMFactory").info("LLMFactory reset complete.")