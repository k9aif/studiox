# SPDX-License-Identifier: Apache-2.0
# Shared, provider-agnostic LLM call — moved out of api/routes.py so
# backend/services/doc_narration_service.py can use the exact same
# dispatch (ollama/watsonx/openai/custom/anthropic) as canvas-suggestion
# generation, instead of hardcoding its own Ollama-only call. Ravi: "my
# concern is that the LLM would not be consistent here at all... remove
# the wiring to the qwen model. Only when a user or myself sets up a LLM
# using the setup then it can be used" — this is the one place either
# feature calls out to a model, driven entirely by the caller's own
# endpoint/provider/model/api_key, never a hardcoded default.

import requests as http


def call_llm(
    endpoint: str, provider: str, model: str, api_key: str, prompt: str,
    timeout: int = 60, max_tokens: int = 2048,
) -> str:
    """Call the configured LLM and return the raw text response. Raises on failure."""
    if provider == "ollama":
        resp = http.post(
            f"{endpoint}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    elif provider == "watsonx":
        headers: dict = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = http.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    elif provider in ("openai", "custom"):
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = http.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    elif provider == "anthropic":
        resp = http.post(
            f"{endpoint}/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": api_key,
                     "anthropic-version": "2023-06-01"},
            json={"model": model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    raise ValueError(f"Unknown provider: {provider}")
