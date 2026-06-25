# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework
#
# Live smoke test — sends a real prompt to Ollama via the full provider-adapter chain.
# Requires Ollama running and reachable at the base_url in config.yaml.
#
# Usage:
#   pytest k9_aif_abb/tests/test_ollama_live.py -v -s
#   python k9_aif_abb/tests/test_ollama_live.py

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "k9_aif_abb" / "config" / "config.yaml"


def load_config() -> dict:
    from k9_aif_abb.k9_utils.config_loader import load_yaml
    return load_yaml(CONFIG_PATH)


def test_ollama_live():
    """Send 'Who is Elon Musk?' through LLMFactory → OllamaProviderAdapter → OllamaLLM."""
    from k9_aif_abb.k9_factories.llm_factory import LLMFactory
    from k9_aif_abb.k9_factories.model_router_factory import ModelRouterFactory
    from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
    from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest

    config = load_config()
    LLMFactory.bootstrap(config)
    ModelRouterFactory.get_router(config)

    req = InferenceRequest(
        prompt="Who is Elon Musk? Answer in two sentences.",
        task_type="general",
        metadata={"test": "test_ollama_live"},
    )

    print("\n--- Sending prompt ---")
    print(f"Prompt: {req.prompt}")
    print(f"Config: {CONFIG_PATH}")

    resp = llm_invoke(config, req)

    print("\n--- Response ---")
    print(f"Model:   {resp.model_alias}")
    print(f"Output:  {resp.output}")
    print(f"Latency: {resp.latency_ms}ms")

    assert resp.output, "Expected a non-empty response from Ollama"
    assert not resp.output.startswith("[WARN]"), f"LLM returned a warning: {resp.output}"

    LLMFactory.reset()


if __name__ == "__main__":
    test_ollama_live()
