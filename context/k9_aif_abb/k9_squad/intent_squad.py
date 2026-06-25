# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
IntentSquad — ABB squad for non-deterministic intent classification.

Position in the execution hierarchy::

    Router ──► intent.in (Kafka)
                    │
        IntentOrchestrator (consumes intent.in)
            → IntentSquad → IntentAgent(s)
                ├── intent resolved ──► domain topic
                └── intent unclear  ──► "please clarify" response

The Router is always the single entry point. IntentOrchestrator is a
Kafka-decoupled consumer — never placed in front of the Router.
IntentSquad runs inside IntentOrchestrator: one or more intent-classification
agents classify the payload, the result is merged back, and IntentOrchestrator
re-publishes to the correct domain topic (or generates a clarification response).

Why a Squad and not just an Agent
----------------------------------
A Squad gives you:
- Multiple classification agents in sequence (e.g. fast rule-based first,
  then LLM fallback, then confidence guard)
- The standard ``flow:`` YAML to wire conditional steps (``when:``)
- A first-class position in the execution hierarchy — visible in Studio,
  traceable in governance, scaffolded by the generator

Overrideable surface (SBB)
--------------------------
``select_agent(payload)``
    Pick which registered agent to call.  Default: first agent that has
    ``classify`` (i.e. is a BaseIntentAgent).  Override for multi-model
    A/B or confidence-based selection.

``merge_intent(payload, intent_result)``
    Decide how the agent result is merged back into the pipeline context.
    Default: spreads ``intent`` and ``confidence`` onto the payload dict.
    Override to add domain keys (e.g. ``"intent_trace"``, ``"routing_hint"``).

``on_low_confidence(payload, intent, confidence)``
    Called when confidence is below ``confidence_threshold`` config key.
    Default: logs a warning and continues — intent is still set.
    Override to escalate to a HIL queue, fall back to a secondary agent,
    or raise so the router treats the event as unroutable.

Usage
-----
Wire via squads.yaml::

    squads:
      IntentSquad:
        description: "Classifies incoming event intent before routing."
        agents:
          - K9IntentAgent
        flow:
          - agent: K9IntentAgent
            result_key: intent_result

The ``execute()`` method ignores the YAML flow and drives agents directly so
it can reliably merge ``intent`` into the returned payload (not just results).
The flow YAML is used only by ``SquadLoader`` to wire agents — it is not
executed step-by-step as in BaseSquad.
"""

import logging
import time
from typing import Any, Dict, Optional

from k9_aif_abb.k9_squad.base_squad import BaseSquad

log = logging.getLogger(__name__)

_INTENT_AGENT_METHOD = "classify"   # duck-type check: agent has this → is an IntentAgent


class IntentSquad(BaseSquad):
    """
    ABB: Pre-router squad that stamps ``intent`` onto the event payload.

    Returns the enriched payload dict (not just agent results) so it can be
    passed directly to ``K9EventRouter.route()``.
    """

    # ── Optional overrides ────────────────────────────────────────────────────

    def select_agent(self, payload: Dict[str, Any]):
        """
        Return the agent instance to use for this payload.

        Default: first agent that has a ``classify`` method (BaseIntentAgent).
        Falls back to ``self.agents[0]`` if none qualify.

        Override for multi-agent selection logic (A/B, load-based, etc.).
        """
        for agent in self.agents:
            if hasattr(agent, _INTENT_AGENT_METHOD):
                return agent
        if self.agents:
            log.warning(
                "[%s] no BaseIntentAgent found — falling back to %s",
                self.squad_id, type(self.agents[0]).__name__,
            )
            return self.agents[0]
        return None

    def merge_intent(
        self,
        payload: Dict[str, Any],
        intent_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge agent result into the enriched payload returned to the Router.

        Default: adds ``intent`` and ``confidence`` keys to the payload.
        Override to add domain-specific keys or transform the intent label.
        """
        return {
            **payload,
            "intent":     intent_result.get("intent", "unknown"),
            "confidence": intent_result.get("confidence", 1.0),
        }

    def on_low_confidence(
        self,
        payload: Dict[str, Any],
        intent: str,
        confidence: float,
    ) -> None:
        """
        Called when classification confidence is below ``confidence_threshold``.

        Default: logs a warning and continues.
        Override to escalate, re-run with a different agent, or raise.
        """
        log.warning(
            "[%s] low-confidence intent=%s confidence=%.2f (threshold=%.2f) — continuing",
            self.squad_id, intent, confidence,
            self.metadata.get("confidence_threshold", 0.5),
        )

    # ── Final — do not override ───────────────────────────────────────────────

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run intent classification and return enriched payload.

        Drives ``select_agent`` → ``agent.execute()`` → ``merge_intent``.
        The returned dict is passed directly to ``K9EventRouter.route()``.
        """
        if not self.agents:
            raise RuntimeError(
                f"[{self.squad_id}] No agents registered — "
                "add at least one K9IntentAgent to the squad."
            )

        agent = self.select_agent(payload)
        if agent is None:
            raise RuntimeError(f"[{self.squad_id}] select_agent() returned None")

        if self.monitor:
            self.monitor.on_squad_start(self.squad_id)

        log.info("[%s] classifying intent via %s", self.squad_id, type(agent).__name__)
        t0 = time.monotonic()
        try:
            intent_result = agent.execute(payload)
        except Exception:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            log.exception(
                "[%s] intent agent %s FAILED elapsed_ms=%d",
                self.squad_id, type(agent).__name__, elapsed_ms,
            )
            raise
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        intent     = intent_result.get("intent", "unknown")
        confidence = float(intent_result.get("confidence", 1.0))
        threshold  = float(self.metadata.get("confidence_threshold", 0.5))

        log.info(
            "[%s] intent=%s confidence=%.2f elapsed_ms=%d",
            self.squad_id, intent, confidence, elapsed_ms,
        )

        if confidence < threshold:
            self.on_low_confidence(payload, intent, confidence)

        if self.monitor:
            self.monitor.on_squad_end(self.squad_id)

        enriched = self.merge_intent(payload, intent_result)
        enriched["squad_id"] = self.squad_id
        enriched["status"]   = "completed"
        return enriched

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Delegates to execute() — kept for consistency with BaseSquad."""
        return self.execute(payload)
