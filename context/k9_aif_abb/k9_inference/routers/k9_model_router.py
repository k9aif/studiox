# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from ..models.inference_request import InferenceRequest
from ..models.inference_response import InferenceResponse
from ..models.route_decision import RouteDecision
from ..catalog.model_catalog import ModelCatalog
from .base_model_router import BaseModelRouter

from k9_aif_abb.k9_factories.llm_factory import LLMFactory
from k9_aif_abb.k9_storage.routing_state_store import RoutingStateStore


_COMPLEXITY_SCORE: dict[str, float] = {
    "reasoning": 0.8,
    "extraction": 0.6,
    "analysis": 0.7,
    "general": 0.3,
    "chat": 0.2,
    "summarization": 0.4,
}

_LATENCY_TIERS = ("realtime", "interactive", "batch")
_COST_TIERS = ("minimal", "standard", "premium")


class K9ModelRouter(BaseModelRouter):
    """
    OOB K9 Model Router
    -------------------
    Weighted-scoring router with session-aware persistence.

    Scoring (higher wins):
      +3  capability match on task_type
      +2  sensitivity=="confidential" and "confidential" in capabilities
      +2  latency_budget matches model's latency_tier
      +2  cost_profile matches model's cost_tier

    Falls back to default_model when no candidate scores > 0.
    All new InferenceRequest fields are Optional — omitting them degrades
    gracefully to pure capability routing (backwards compatible).
    """

    def __init__(
        self,
        catalog: ModelCatalog,
        config: Optional[dict] = None,
        monitor=None,
        state_store: Optional[RoutingStateStore] = None,
    ):
        self.catalog = catalog
        self.config = config or {}
        self.monitor = monitor

        if state_store is None:
            raise ValueError(
                "K9ModelRouter requires a state_store provided by ModelRouterFactory"
            )

        self.state_store = state_store

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    def _resolve_session_id(self, request: InferenceRequest) -> str:
        session_id = getattr(request, "session_id", None)
        return str(session_id) if session_id else str(uuid.uuid4())

    def _resolve_user_id(self, request: InferenceRequest) -> str:
        user_id = getattr(request, "user_id", None)
        return str(user_id) if user_id else "anonymous"

    def _persist_request_context(
        self,
        request: InferenceRequest,
    ) -> tuple[str, str, int]:
        session_id = self._resolve_session_id(request)
        user_id = self._resolve_user_id(request)

        self.state_store.ensure_session(session_id=session_id, user_id=user_id)

        turn_id = self.state_store.append_turn(
            session_id=session_id,
            role="USER",
            content=request.prompt,
            token_count=None,
            compressed_flag=False,
        )

        return session_id, user_id, turn_id

    def _persist_route_decision(
        self,
        session_id: str,
        turn_id: int,
        decision: RouteDecision,
        request: InferenceRequest,
    ) -> None:
        complexity = _COMPLEXITY_SCORE.get(request.task_type or "general", 0.5)
        governance = 1.0 if getattr(request, "sensitivity", None) == "confidential" else 0.0

        self.state_store.record_routing_decision(
            session_id=session_id,
            turn_id=turn_id,
            selected_model=decision.model_alias,
            routing_reason=decision.rationale,
            complexity_score=complexity,
            governance_score=governance,
            prompt_hash=None,
            metadata={
                "provider": decision.provider,
                "router": "K9ModelRouter",
                "score": decision.score,
            },
        )

        self.state_store.update_model_affinity(
            session_id=session_id,
            model_name=decision.model_alias,
        )

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def _score_candidate(self, alias: str, meta: dict, request: InferenceRequest) -> float:
        score = 0.0
        caps = meta.get("capabilities", [])

        if request.task_type and request.task_type in caps:
            score += 3.0

        if getattr(request, "sensitivity", None) == "confidential" and "confidential" in caps:
            score += 2.0

        if request.latency_budget and request.latency_budget == meta.get("latency_tier"):
            score += 2.0

        if request.cost_profile and request.cost_profile == meta.get("cost_tier"):
            score += 2.0

        return score

    def route(self, request: InferenceRequest) -> RouteDecision:
        best_alias: Optional[str] = None
        best_score = -1.0

        for alias, meta in self.catalog.models.items():
            score = self._score_candidate(alias, meta, request)
            if score > best_score:
                best_score = score
                best_alias = alias

        # Fall back to default when nothing matched (best_score == 0 means
        # no capability/sensitivity/latency/cost signals fired at all)
        if best_alias is None or best_score == 0.0:
            best_alias = self.catalog.get_default_model()
            best_score = 0.0

        if not best_alias:
            raise RuntimeError("ModelRouter: no model alias resolved")

        model_info = self.catalog.get_model(best_alias)

        rationale_parts = ["K9 weighted-score routing"]
        if best_score > 0:
            rationale_parts.append(f"score={best_score:.1f}")
        if request.latency_budget:
            rationale_parts.append(f"latency={request.latency_budget}")
        if request.cost_profile:
            rationale_parts.append(f"cost={request.cost_profile}")

        return RouteDecision(
            model_alias=best_alias,
            provider=model_info.get("provider"),
            score=best_score if best_score > 0 else None,
            rationale="; ".join(rationale_parts),
        )

    # ------------------------------------------------------------------
    # Sync Invoke
    # ------------------------------------------------------------------
    def invoke(self, request: InferenceRequest) -> InferenceResponse:
        session_id, user_id, turn_id = self._persist_request_context(request)

        decision = self.route(request)
        self._persist_route_decision(session_id, turn_id, decision, request)

        model_info = self.catalog.get_model(decision.model_alias)
        llm_ref = model_info.get("llm_ref")

        llm = LLMFactory.get(llm_ref)

        if hasattr(llm, "invoke"):
            result = llm.invoke(request.prompt)
        elif hasattr(llm, "generate"):
            result = asyncio.run(llm.generate(request.prompt))
        elif hasattr(llm, "chat"):
            result = llm.chat(request.prompt)
        elif callable(llm):
            result = llm(request.prompt)
        else:
            raise AttributeError(
                f"{llm.__class__.__name__} has no supported inference method "
                "(expected invoke, generate, chat, or __call__)"
            )

        return InferenceResponse(
            output=result,
            model_alias=decision.model_alias,
            provider=model_info.get("provider"),
        )

    # ------------------------------------------------------------------
    # Async Invoke
    # ------------------------------------------------------------------
    async def ainvoke(self, request: InferenceRequest) -> InferenceResponse:
        session_id, user_id, turn_id = self._persist_request_context(request)

        decision = self.route(request)
        self._persist_route_decision(session_id, turn_id, decision, request)

        model_info = self.catalog.get_model(decision.model_alias)
        llm_ref = model_info.get("llm_ref")

        llm = LLMFactory.get(llm_ref)

        if hasattr(llm, "ainvoke") and callable(llm.ainvoke):
            result = await llm.ainvoke(request.prompt)

        elif hasattr(llm, "agenerate") and callable(llm.agenerate):
            result = await llm.agenerate(request.prompt)

        elif hasattr(llm, "generate") and callable(llm.generate):
            result = await llm.generate(request.prompt)

        elif hasattr(llm, "invoke") and callable(llm.invoke):
            result = llm.invoke(request.prompt)

        elif callable(llm):
            result = llm(request.prompt)

        else:
            raise AttributeError(
                f"{llm.__class__.__name__} has no supported inference method"
            )

        return InferenceResponse(
            output=str(result),
            model_alias=decision.model_alias,
            provider=model_info.get("provider"),
        )