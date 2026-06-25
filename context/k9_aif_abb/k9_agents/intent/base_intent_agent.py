# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
BaseIntentAgent — ABB abstract skeleton for intent classification.

Inheritance hierarchy::

    BaseAgent
      └── BaseIntentAgent          (loop skeleton — ABB, this file)
            └── K9IntentAgent      (LLM-driven OOB)
                  └── MyIntentAgent  (domain SBB — overrides only what differs)

Overrideable surface
--------------------
``classify(payload)`` — **abstract** — the only method an SBB *must* implement.
    Return a raw intent string.  ``execute()`` calls this and routes through
    ``normalize_intent()`` and error-handling automatically.

``normalize_intent(raw)`` — convert raw classifier output to a clean label.
    Default: lowercase, first whitespace-delimited token.
    Override when the LLM returns structured JSON or domain-specific formats.

``fallback_intent(payload)`` — intent label used when ``classify()`` raises or
    returns empty.  Default: ``payload["event_type"]`` → ``"unknown"``.
    Override to implement domain-specific safe defaults.

``confidence(result)`` — extract a 0.0–1.0 confidence score from the
    classification result dict.  Default returns ``result.get("confidence", 1.0)``.
    Override when a downstream guard or IntentSquad needs confidence gating.

``execute()`` is **final** — do not override.  It calls ``classify()``,
``normalize_intent()``, ``confidence()``, and ``fallback_intent()`` in order,
publishes an ``IntentClassified`` event, and returns::

    {"intent": "<label>", "confidence": <float>}
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

log = logging.getLogger(__name__)


class BaseIntentAgent(BaseAgent):
    """
    ABB: Abstract skeleton for intent classification agents.

    Sits inside an IntentSquad, which is used by IntentOrchestrator —
    a Kafka-decoupled consumer on the `intent.in` topic. The Router is
    always the single entry point; IntentOrchestrator is never placed
    in front of it.

    Minimal SBB implementation::

        class MyIntentAgent(K9IntentAgent):
            layer = "MyApp IntentAgent SBB"

            def classify(self, payload):
                # call your own rules, ML model, or external service
                return my_classifier.predict(payload["text"])

    Or configure entirely via YAML (no code) using K9IntentAgent with
    ``intent_map`` entries covering all expected event types.
    """

    layer: str = "BaseIntentAgent"

    # ── Abstract — SBBs must implement ───────────────────────────────────────

    @abstractmethod
    def classify(self, payload: Dict[str, Any]) -> str:
        """
        Classify the intent of the incoming payload.

        Args:
            payload: the enriched context passed through the pipeline.

        Returns:
            A raw intent string (will be normalized by ``normalize_intent``).

        Raises:
            Any exception — ``execute()`` catches and routes to ``fallback_intent``.
        """
        raise NotImplementedError

    # ── Optional overrides ────────────────────────────────────────────────────

    def normalize_intent(self, raw: str) -> str:
        """
        Convert raw classifier output to a clean intent label.

        Default: lowercase, first whitespace-delimited token.
        Override when the LLM returns JSON, multi-word labels, or mapped codes.
        """
        token = raw.strip().lower().split()[0] if raw.strip() else ""
        return token or "unknown"

    def fallback_intent(self, payload: Dict[str, Any]) -> str:
        """
        Intent label to use when ``classify()`` raises or returns empty.

        Default: ``payload["event_type"]`` verbatim, or ``"unknown"``.
        Override to enforce domain-safe defaults (e.g. ``"requires_review"``).
        """
        return str(payload.get("event_type", "unknown")) or "unknown"

    def confidence(self, result: Dict[str, Any]) -> float:
        """
        Extract a confidence score (0.0–1.0) from the classification result.

        Default: ``result.get("confidence", 1.0)`` — rule-based hits return 1.0.
        Override when ``classify()`` returns a scored result and IntentSquad
        needs to gate on confidence before passing intent to the Router.
        """
        return float(result.get("confidence", 1.0))

    # ── Final — do not override ───────────────────────────────────────────────

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Drive the classify → normalize → fallback pipeline. Do not override."""
        try:
            raw = self.classify(payload)
            intent = self.normalize_intent(raw) if raw else self.fallback_intent(payload)
        except Exception as exc:
            log.warning("[%s] classify() raised %s — using fallback_intent", self.layer, exc)
            intent = self.fallback_intent(payload)

        result = {"intent": intent}
        score = self.confidence(result)
        result["confidence"] = score

        log.info("[%s] intent=%s confidence=%.2f", self.layer, intent, score)
        self.publish_event({"type": "IntentClassified", "intent": intent, "confidence": score})
        return result
