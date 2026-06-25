# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework
# k9_aif_abb/k9_adapters/crewai/k9x_litellm_bridge_adapter.py
"""
K9XLiteLLMBridgeAdapter — bridges CrewAI 1.14+ agents to K9-AIF's model router.

Extends crewai.llms.base_llm.BaseLLM (Pydantic BaseModel + ABC).
Only call() is abstract — all other BaseLLM methods retain their defaults.

CrewAI agents are completely unaware of which LLM is serving them.
They call llm.call(messages) as always. This adapter intercepts that call,
routes it through K9ModelRouter (weighted scoring: task_type, cost,
latency, sensitivity), persists the routing decision, and returns the
response — all transparently.

This is the missing piece that makes K9-AIF a true AI motherboard:
every LLM call, from any framework, governed and routed by K9-AIF.

Usage in crew loader:
    from k9_aif_abb.k9_adapters.crewai.k9x_litellm_bridge_adapter import K9XLiteLLMBridgeAdapter

    llm = K9XLiteLLMBridgeAdapter(
        k9_config=config,
        task_type="reasoning",
        agent_name="MissionAssessmentAgent",
    )
    agent = Agent(role=..., goal=..., llm=llm)

Verified against CrewAI 1.14.6.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field, PrivateAttr

from crewai.llms.base_llm import BaseLLM
from crewai.types.usage_metrics import UsageMetrics

from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke

if TYPE_CHECKING:
    from crewai.tools.base_tool import BaseTool
    from crewai.agents.agent_builder.base_agent import BaseAgent
    from crewai.task import Task

log = logging.getLogger("K9XLiteLLMBridgeAdapter")


class K9XLiteLLMBridgeAdapter(BaseLLM):
    """
    K9-AIF LLM bridge for CrewAI 1.14+.

    Implements BaseLLM.call() to route through K9ModelRouter.
    All other BaseLLM methods retain their default implementations.

    Fields (Pydantic):
        model:      Fixed to "k9x-routed/<task_type>" — identifies this bridge
        provider:   Fixed to "k9x"
        task_type:  K9-AIF task_type for model scoring (default: "general")
        agent_name: Used in audit event metadata

    Private (not serialised):
        _k9_config: K9-AIF config dict (inference section required)
    """

    # BaseLLM required field
    model: str = "k9x-routed/general"
    provider: str = "k9x"
    is_litellm: bool = False

    # K9X bridge fields
    task_type: str = Field(default="general")
    agent_name: str = Field(default="CrewAIAgent")
    sensitivity: Optional[str] = Field(default=None)

    # Config stored privately — not serialised, not exposed to CrewAI
    _k9_config: dict[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        k9_config: dict[str, Any] | None = None,
        task_type: str = "general",
        agent_name: str = "CrewAIAgent",
        sensitivity: str | None = None,
        **kwargs,
    ):
        super().__init__(
            model=f"k9x-routed/{task_type}",
            provider="k9x",
            is_litellm=False,
            task_type=task_type,
            agent_name=agent_name,
            sensitivity=sensitivity,
            stop=[],
            additional_params={},
            **kwargs,
        )
        self._k9_config = k9_config or {}
        log.info(
            "[K9XBridge] Initialised — agent: '%s', task_type: %s",
            agent_name,
            task_type,
        )

    # ── Message extraction ───────────────────────────────────────────────────

    def _extract_text(self, messages: str | list[Any]) -> str:
        """Extract plain text from str or list[LLMMessage]."""
        if isinstance(messages, str):
            return messages

        if isinstance(messages, list):
            parts = []
            for m in messages:
                if isinstance(m, dict):
                    content = m.get("content", "")
                elif hasattr(m, "content"):
                    content = m.content
                else:
                    content = str(m)

                if isinstance(content, list):
                    # Multimodal content blocks
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                elif content:
                    parts.append(str(content))
            return "\n".join(parts)

        return str(messages) if messages else ""

    # ── BaseLLM abstract method ──────────────────────────────────────────────

    def call(
        self,
        messages: str | list[Any],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type | None = None,
    ) -> str:
        """Route this LLM call through K9-AIF's ModelRouter."""
        prompt = self._extract_text(messages)

        req = InferenceRequest(
            prompt=prompt,
            task_type=self.task_type,
            sensitivity=self.sensitivity,
            metadata={
                "agent": self.agent_name,
                "bridge": "K9XLiteLLMBridgeAdapter",
                "crewai_version": "1.14+",
            },
        )

        try:
            resp = llm_invoke(self._k9_config, req)
            log.debug(
                "[K9XBridge] %s — model: %s — latency: %sms",
                self.agent_name,
                resp.model_alias,
                getattr(resp, "latency_ms", "?"),
            )
            return resp.output.strip()
        except RuntimeError as exc:
            log.error("[K9XBridge] LLM unavailable for '%s': %s", self.agent_name, exc)
            return f"[K9X ERROR] LLM unavailable: {exc}"

    # ── BaseLLM overrides ────────────────────────────────────────────────────

    def get_context_window_size(self) -> int:
        return 32768

    def supports_stop_words(self) -> bool:
        return False

    def supports_multimodal(self) -> bool:
        return False

    def get_token_usage_summary(self) -> UsageMetrics:
        return UsageMetrics()

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "task_type": self.task_type,
            "agent_name": self.agent_name,
        }
