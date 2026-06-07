# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework — k9_utils/llm_invoke.py
#
# Framework-level LLM invocation utility.
#
# Thin wrapper around ModelRouterFactory.get_router().invoke() that:
#   1. Raises RuntimeError if the LLM backend is unreachable ([WARN] response).
#   2. Publishes an LLMCall trace event via an optional registered callback
#      (e.g. SSE push, metrics sink — wired in by the application at startup).
#
# Usage in agents:
#   from k9_aif_abb.k9_utils.llm_invoke import llm_invoke
#   resp = llm_invoke(self.config, req)
#
# Optional callback registration (call once at app startup):
#   from k9_aif_abb.k9_utils.llm_invoke import register_trace_callback
#   register_trace_callback(my_push_fn)

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

from k9_aif_abb.k9_factories.model_router_factory import ModelRouterFactory
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_inference.models.inference_response import InferenceResponse

log = logging.getLogger(__name__)

# Optional trace callback — registered by the application at startup.
# Signature: (event: dict) -> None
_trace_callback: Optional[Callable[[Dict[str, Any]], None]] = None


def register_trace_callback(fn: Callable[[Dict[str, Any]], None]) -> None:
    """
    Register a callback that receives an LLMCall event dict after every
    successful invocation.  Call once at application startup.

    The callback is fire-and-forget: exceptions are caught and logged so
    a failing callback never breaks agent execution.
    """
    global _trace_callback
    _trace_callback = fn
    log.info("[llm_invoke] trace callback registered: %s", fn)


def llm_invoke(config: Dict[str, Any], request: InferenceRequest) -> InferenceResponse:
    """
    Invoke the LLM router and return the response.

    Args:
        config:  Application config dict (must contain ``inference`` section).
        request: :class:`InferenceRequest` describing the prompt and task type.

    Returns:
        :class:`InferenceResponse` with model output and metadata.

    Raises:
        RuntimeError: if the LLM backend is unreachable or returns an empty
            response (OllamaLLM signals this with a ``[WARN]`` prefix).
    """
    router = ModelRouterFactory.get_router(config)
    t0 = time.monotonic()
    resp = router.invoke(request)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # OllamaLLM silently returns "[WARN]..." on connection failure — fail hard.
    if not resp.output or resp.output.startswith("[WARN]"):
        raise RuntimeError(
            f"LLM backend unavailable "
            f"(agent={(request.metadata or {}).get('agent', '?')} "
            f"model={resp.model_alias}): {resp.output}"
        )

    if _trace_callback is not None:
        try:
            tokens = (resp.token_usage or {}) if resp.token_usage else {}
            _trace_callback({
                "type":       "LLMCall",
                "agent":      (request.metadata or {}).get("agent", "unknown"),
                "task_type":  request.task_type or "general",
                "model":      resp.model_alias or "?",
                "provider":   resp.provider or "unknown",
                "latency_ms": resp.latency_ms or elapsed_ms,
                "tokens_in":  tokens.get("prompt", tokens.get("input")),
                "tokens_out": tokens.get("completion", tokens.get("output")),
            })
        except Exception as exc:
            log.warning("[llm_invoke] trace callback failed: %s", exc)

    log.info(
        "[llm_invoke] agent=%s task=%s model=%s latency_ms=%d",
        (request.metadata or {}).get("agent", "?"),
        request.task_type,
        resp.model_alias,
        elapsed_ms,
    )
    return resp
