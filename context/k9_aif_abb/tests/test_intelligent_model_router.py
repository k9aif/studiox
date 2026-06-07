# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework
#
# test_intelligent_model_router.py — Phase 1 scoring tests for K9ModelRouter
#
# Tests route() directly via a mock state_store — no LLM or DB required.
#
# Run:
#   pytest k9_aif_abb/tests/test_intelligent_model_router.py -v

from unittest.mock import MagicMock

import pytest

from k9_aif_abb.k9_inference.catalog.model_catalog import ModelCatalog
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_inference.routers.k9_model_router import K9ModelRouter, _COMPLEXITY_SCORE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _catalog(extra_models: dict | None = None) -> ModelCatalog:
    """Three-model catalog with latency/cost tiers on two of them."""
    models = {
        "fast": {
            "provider": "ollama",
            "llm_ref": "fast",
            "capabilities": ["chat", "summarization"],
            "latency_tier": "realtime",
            "cost_tier": "minimal",
        },
        "smart": {
            "provider": "ollama",
            "llm_ref": "smart",
            "capabilities": ["reasoning", "analysis"],
            "latency_tier": "interactive",
            "cost_tier": "standard",
        },
        "secure": {
            "provider": "ollama",
            "llm_ref": "secure",
            "capabilities": ["confidential", "enterprise"],
            "latency_tier": "batch",
            "cost_tier": "premium",
        },
    }
    if extra_models:
        models.update(extra_models)
    return ModelCatalog({"default_model": "fast", "models": models})


def _router(catalog: ModelCatalog | None = None) -> K9ModelRouter:
    mock_store = MagicMock()
    mock_store.ensure_session.return_value = None
    mock_store.append_turn.return_value = 1
    mock_store.record_routing_decision.return_value = None
    mock_store.update_model_affinity.return_value = None
    return K9ModelRouter(catalog=catalog or _catalog(), state_store=mock_store)


# ---------------------------------------------------------------------------
# 1. Capability-only routing (no latency/cost hints)
# ---------------------------------------------------------------------------

class TestCapabilityRouting:

    def test_task_type_selects_matching_model(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="reasoning"))
        assert decision.model_alias == "smart"

    def test_confidential_sensitivity_routes_to_secure_model(self):
        decision = _router().route(InferenceRequest(
            prompt="x", task_type="enterprise", sensitivity="confidential"
        ))
        assert decision.model_alias == "secure"

    def test_unknown_task_type_falls_back_to_default(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="unknown_task"))
        assert decision.model_alias == "fast"

    def test_no_task_type_falls_back_to_default(self):
        decision = _router().route(InferenceRequest(prompt="x"))
        assert decision.model_alias == "fast"

    def test_chat_task_selects_fast_model(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="chat"))
        assert decision.model_alias == "fast"

    def test_analysis_task_selects_smart_model(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="analysis"))
        assert decision.model_alias == "smart"


# ---------------------------------------------------------------------------
# 2. Latency/cost hints boost the right candidate
# ---------------------------------------------------------------------------

class TestLatencyAndCostScoring:

    def test_realtime_latency_budget_selects_fast(self):
        decision = _router().route(InferenceRequest(
            prompt="x", latency_budget="realtime"
        ))
        assert decision.model_alias == "fast"

    def test_premium_cost_profile_selects_secure(self):
        decision = _router().route(InferenceRequest(
            prompt="x", cost_profile="premium"
        ))
        assert decision.model_alias == "secure"

    def test_capability_plus_latency_hint_outscores_capability_only(self):
        # "chat" matches fast (+3 cap) AND realtime latency (+2) = 5
        # "summarization" also matches fast — same model, but let's verify score
        decision = _router().route(InferenceRequest(
            prompt="x", task_type="chat", latency_budget="realtime"
        ))
        assert decision.model_alias == "fast"
        assert decision.score == 5.0

    def test_mismatched_latency_does_not_boost_wrong_model(self):
        # batch latency_budget should match "secure" (+2), but "reasoning" capability
        # on "smart" is +3 — smart should win
        decision = _router().route(InferenceRequest(
            prompt="x", task_type="reasoning", latency_budget="batch"
        ))
        assert decision.model_alias == "smart"

    def test_cost_and_latency_together_breaks_tie(self):
        # no task_type — only cost/latency signals
        decision = _router().route(InferenceRequest(
            prompt="x", latency_budget="batch", cost_profile="premium"
        ))
        assert decision.model_alias == "secure"
        assert decision.score == 4.0


# ---------------------------------------------------------------------------
# 3. RouteDecision score field
# ---------------------------------------------------------------------------

class TestScoreField:

    def test_score_populated_when_signal_fired(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="reasoning"))
        assert decision.score == 3.0

    def test_score_is_none_when_fallback_used(self):
        decision = _router().route(InferenceRequest(prompt="x"))
        assert decision.score is None

    def test_score_none_on_unknown_task(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="unknown_xyz"))
        assert decision.score is None

    def test_max_score_all_signals(self):
        # reasoning(+3) + batch latency(+2) + premium cost(+2) on "secure" = 2+2=4
        # But "smart" gets reasoning+3 while "secure" gets latency+cost=4 — tie at 4? No:
        # "smart": reasoning(+3), interactive latency(no match), standard cost(no match) = 3
        # "secure": reasoning not in caps, batch latency(+2), premium cost(+2) = 4
        decision = _router().route(InferenceRequest(
            prompt="x", task_type="reasoning", latency_budget="batch", cost_profile="premium"
        ))
        # secure wins (4 > 3)
        assert decision.model_alias == "secure"
        assert decision.score == 4.0

    def test_confidential_sensitivity_contributes_to_score(self):
        decision = _router().route(InferenceRequest(
            prompt="x", sensitivity="confidential"
        ))
        assert decision.model_alias == "secure"
        assert decision.score == 2.0


# ---------------------------------------------------------------------------
# 4. Rationale string
# ---------------------------------------------------------------------------

class TestRationale:

    def test_rationale_contains_score(self):
        decision = _router().route(InferenceRequest(prompt="x", task_type="reasoning"))
        assert "score=3.0" in decision.rationale

    def test_rationale_contains_latency_when_provided(self):
        decision = _router().route(InferenceRequest(
            prompt="x", task_type="chat", latency_budget="realtime"
        ))
        assert "latency=realtime" in decision.rationale

    def test_rationale_no_score_on_fallback(self):
        decision = _router().route(InferenceRequest(prompt="x"))
        assert "score=" not in decision.rationale

    def test_rationale_contains_cost_when_provided(self):
        decision = _router().route(InferenceRequest(
            prompt="x", cost_profile="standard"
        ))
        assert "cost=standard" in decision.rationale


# ---------------------------------------------------------------------------
# 5. Complexity and governance scores persisted
# ---------------------------------------------------------------------------

class TestPersistenceScores:

    def _route_and_capture(self, request: InferenceRequest):
        mock_store = MagicMock()
        mock_store.ensure_session.return_value = None
        mock_store.append_turn.return_value = 1
        router = K9ModelRouter(catalog=_catalog(), state_store=mock_store)
        router.route(request)
        # invoke _persist_route_decision directly to inspect store call
        from k9_aif_abb.k9_inference.models.route_decision import RouteDecision
        decision = RouteDecision(model_alias="fast", provider="ollama", score=3.0)
        router._persist_route_decision("sess-1", 1, decision, request)
        return mock_store.record_routing_decision.call_args

    def test_reasoning_task_gets_high_complexity(self):
        call = self._route_and_capture(InferenceRequest(prompt="x", task_type="reasoning"))
        assert call.kwargs["complexity_score"] == 0.8

    def test_general_task_gets_low_complexity(self):
        call = self._route_and_capture(InferenceRequest(prompt="x", task_type="general"))
        assert call.kwargs["complexity_score"] == 0.3

    def test_unknown_task_gets_default_complexity(self):
        call = self._route_and_capture(InferenceRequest(prompt="x", task_type="unknown"))
        assert call.kwargs["complexity_score"] == 0.5

    def test_confidential_sensitivity_governance_score_is_one(self):
        call = self._route_and_capture(InferenceRequest(
            prompt="x", sensitivity="confidential"
        ))
        assert call.kwargs["governance_score"] == 1.0

    def test_non_confidential_governance_score_is_zero(self):
        call = self._route_and_capture(InferenceRequest(prompt="x"))
        assert call.kwargs["governance_score"] == 0.0

    def test_score_included_in_metadata(self):
        call = self._route_and_capture(InferenceRequest(prompt="x", task_type="chat"))
        assert "score" in call.kwargs["metadata"]


# ---------------------------------------------------------------------------
# 6. Empty catalog / edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_raises_when_no_model_resolved(self):
        empty_catalog = ModelCatalog({"models": {}})
        router = _router(catalog=empty_catalog)
        with pytest.raises(RuntimeError, match="no model alias resolved"):
            router.route(InferenceRequest(prompt="x"))

    def test_single_model_catalog_always_wins(self):
        catalog = ModelCatalog({
            "default_model": "only",
            "models": {
                "only": {"provider": "ollama", "capabilities": ["general"]},
            },
        })
        decision = _router(catalog=catalog).route(InferenceRequest(prompt="x", task_type="general"))
        assert decision.model_alias == "only"

    def test_backwards_compatible_no_latency_budget(self):
        # Old-style request with no new fields — must still route by capability
        req = InferenceRequest(prompt="hello", task_type="chat")
        assert req.latency_budget is None
        assert req.cost_profile is None
        decision = _router().route(req)
        assert decision.model_alias == "fast"

    def test_complexity_score_table_covers_all_documented_types(self):
        for task_type in ("reasoning", "extraction", "analysis", "general", "chat", "summarization"):
            assert task_type in _COMPLEXITY_SCORE
