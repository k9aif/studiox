# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
IntentOrchestrator — OOB Kafka-decoupled intent resolution orchestrator.

Consumes events from ``intent.in`` (published by K9EventRouter when
``event_type`` is not in the routing table).  Runs IntentSquad →
K9IntentAgent to classify intent, then:

- Intent resolved (confidence ≥ threshold)  →  re-publishes to domain topic
- Intent unclear                             →  publishes "please clarify" response

Position in the topology::

    Router ──► intent.in (Kafka)
                    │
        IntentOrchestrator  ← this class
            → IntentSquad → IntentAgent(s)
                ├── intent resolved ──► domain topic
                └── intent unclear  ──► response topic ("please clarify")

OOB behaviour
-------------
- IntentSquad is self-bootstrapped with ``K9IntentAgent`` (LLM-driven).
  ``K9IntentAgent`` first checks ``intent_map`` (zero-latency rule lookup),
  then falls back to LLM.  Configure ``intent_map`` in ``config.yaml`` to
  avoid LLM calls for known intents.
- ``confidence_threshold`` (default 0.6) controls when clarification is sent.
- ``routing.table`` maps intent labels → Kafka topics (same table as Router).

Configuration (``config.yaml``)
--------------------------------
::

    routing:
      intent_topic:        intent.in      # Router publishes here
      response_topic:      responses.out  # clarification replies go here
      confidence_threshold: 0.6
      table:                              # intent label → domain topic
        fraud:    fraud.in
        claims:   claims.in
        document: documents.in

      intent_map:                         # fast-path rule lookup for K9IntentAgent
        fraud_report: fraud
        claim_form:   claims

SBB override
------------
Three extension points — override only what differs:

1. **Replace intent agent** — pass a custom squad at construction::

       squad = IntentSquad("MySquad", agents=[MyRulesIntentAgent(config=cfg)])
       orch = IntentOrchestrator(config=cfg, squad=squad, message_bus=bus)

2. **Override execute_flow** — add pre/post processing::

       class AcmeIntentOrchestrator(IntentOrchestrator):
           layer = "AcmeIntentOrchestrator SBB"

           def execute_flow(self, payload):
               payload = self._pre_enrich(payload)   # domain enrichment
               result  = super().execute_flow(payload)
               self._audit(result)                   # domain audit trail
               return result

3. **Override clarification message** — customise the "please clarify" text::

       class AcmeIntentOrchestrator(IntentOrchestrator):
           def _clarification_message(self, intent, confidence, payload):
               return f"Could not understand your request (detected: {intent}). Please rephrase."
"""

import logging
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator

log = logging.getLogger(__name__)

_DEFAULT_CLARIFICATION = (
    "I was unable to determine the intent of your request. "
    "Could you please clarify what you would like to do?"
)


class IntentOrchestrator(BaseOrchestrator):
    """
    OOB IntentOrchestrator — self-bootstrapped with K9IntentAgent + IntentSquad.
    """

    layer = "IntentOrchestrator OOB"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        squad=None,
        monitor=None,
        message_bus=None,
        governance=None,
    ):
        super().__init__(
            config=config,
            monitor=monitor,
            message_bus=message_bus,
            governance=governance,
        )
        routing_cfg = self.config.get("routing", {})
        self._table: Dict[str, str] = routing_cfg.get("table", {})
        self._response_topic: str = routing_cfg.get("response_topic", "responses.out")
        self._threshold: float = float(routing_cfg.get("confidence_threshold", 0.6))

        self._intent_squad = squad or self._build_default_squad()
        log.info(
            "[%s] ready | threshold=%.2f | response_topic=%s | table=%s",
            self.layer, self._threshold, self._response_topic, list(self._table.keys()),
        )

    # ------------------------------------------------------------------
    def _build_default_squad(self):
        """Bootstrap IntentSquad + K9IntentAgent from config. SBBs replace via constructor."""
        from k9_aif_abb.k9_agents.intent.k9_intent_agent import K9IntentAgent
        from k9_aif_abb.k9_squad.intent_squad import IntentSquad

        agent_cfg = {**self.config, **self.config.get("routing", {})}
        agent = K9IntentAgent(config=agent_cfg)
        squad = IntentSquad(squad_id="K9IntentSquad", agents=[agent])
        squad.metadata = self.config.get("routing", {})
        return squad

    # ------------------------------------------------------------------
    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify intent and route — or ask for clarification.

        SBBs override this to add pre/post processing without re-implementing
        the core classification and dispatch logic.
        """
        log.info("[%s] classifying intent for event_type=%r", self.layer, payload.get("event_type"))

        self.publish_status("intent_classification_started", {"event_type": payload.get("event_type")})

        enriched = self._intent_squad.execute(payload)
        intent = enriched.get("intent", "unknown")
        confidence = float(enriched.get("confidence", 0.0))

        log.info("[%s] intent=%r confidence=%.2f threshold=%.2f", self.layer, intent, confidence, self._threshold)

        if confidence >= self._threshold and intent not in ("unknown", ""):
            topic = self._table.get(intent)
            if topic:
                dispatch_payload = {**payload, "intent": intent, "confidence": confidence}
                self._publish(topic, dispatch_payload)
                log.info("[%s] routed: intent=%r → %s", self.layer, intent, topic)
                self.publish_status("intent_resolved", {"intent": intent, "topic": topic})
                return {"status": "routed", "intent": intent, "topic": topic, "confidence": confidence}

            log.warning("[%s] intent=%r resolved but no topic mapping — sending clarification", self.layer, intent)

        # Intent unclear or unmapped — ask for clarification
        clarification = {
            "type": "clarification_required",
            "message": self._clarification_message(intent, confidence, payload),
            "detected_intent": intent,
            "confidence": confidence,
            "original_payload": payload,
        }
        self._publish(self._response_topic, clarification)
        log.info("[%s] clarification sent: intent=%r confidence=%.2f", self.layer, intent, confidence)
        self.publish_status("clarification_required", {"intent": intent, "confidence": confidence})
        return {"status": "clarification_required", "intent": intent, "confidence": confidence}

    # ------------------------------------------------------------------
    def _clarification_message(
        self,
        intent: str,
        confidence: float,
        payload: Dict[str, Any],
    ) -> str:
        """Override to customise the clarification text for your domain."""
        return _DEFAULT_CLARIFICATION

    # ------------------------------------------------------------------
    def _publish(self, topic: str, event: Dict[str, Any]) -> None:
        """Publish to topic via message_bus."""
        if self.message_bus:
            if hasattr(self.message_bus, "publish_to"):
                self.message_bus.publish_to(topic, event)
            else:
                self.message_bus.publish(event)
