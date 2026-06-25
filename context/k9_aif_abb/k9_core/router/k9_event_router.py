# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9EventRouter — OOB Kafka-aware event router.

The Router is the **single entry point** for all events.  It never contains
classification logic — routing is either deterministic (event_type in the
routing table) or delegated to the IntentOrchestrator via the intent topic.

Routing logic
-------------
1. ``event_type`` found in ``routing.table`` config  →  publish to domain topic
2. ``event_type`` not found                          →  publish to ``intent.in``
   IntentOrchestrator picks it up, classifies intent, re-publishes to the
   correct domain topic (or sends a "please clarify" response).

Configuration (``config.yaml``)
--------------------------------
::

    routing:
      intent_topic: intent.in          # fallback topic when intent unknown
      table:                           # event_type → topic mappings
        claims_submitted: claims.in
        fraud_alert:      fraud.in
        doc_uploaded:     documents.in

SBB override
------------
Extend and override ``route()`` for custom routing logic::

    class AcmeRouter(K9EventRouter):
        layer = "AcmeRouter SBB"

        def route(self, payload):
            # add pre-routing enrichment, auth checks, etc.
            payload = self._enrich(payload)
            return super().route(payload)
"""

import logging
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.router.base_router import BaseRouter

log = logging.getLogger(__name__)


class K9EventRouter(BaseRouter):
    """
    OOB event router — deterministic routing with IntentOrchestrator fallback.
    """

    layer = "K9EventRouter OOB"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
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
        self._intent_topic: str = routing_cfg.get("intent_topic", "intent.in")

        log.info(
            "[%s] routing table: %d entries | intent_topic=%s",
            self.layer, len(self._table), self._intent_topic,
        )

    def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route the event.

        Returns a dict with:
          ``routed``    — always True
          ``topic``     — topic the event was published to
          ``event_type``— original event_type from payload
          ``strategy``  — "deterministic" or "intent_required"
        """
        event_type = payload.get("event_type", "")
        topic = self._table.get(event_type)

        if topic:
            log.info("[%s] deterministic: event_type=%r → %s", self.layer, event_type, topic)
            self._dispatch(topic, payload, strategy="deterministic")
            return {
                "routed": True,
                "topic": topic,
                "event_type": event_type,
                "strategy": "deterministic",
            }

        log.info(
            "[%s] non-deterministic: event_type=%r not in table → %s",
            self.layer, event_type, self._intent_topic,
        )
        self._dispatch(self._intent_topic, payload, strategy="intent_required")
        return {
            "routed": True,
            "topic": self._intent_topic,
            "event_type": event_type,
            "strategy": "intent_required",
        }

    # ------------------------------------------------------------------
    def _dispatch(self, topic: str, payload: Dict[str, Any], strategy: str = "") -> None:
        """Publish payload to the given topic via message_bus."""
        if self.message_bus:
            if hasattr(self.message_bus, "publish_to"):
                self.message_bus.publish_to(topic, payload)
            else:
                self.message_bus.publish(payload)
        if self.monitor:
            self.monitor.record_event({
                "type": "EventRouted",
                "event_type": payload.get("event_type"),
                "topic": topic,
                "strategy": strategy,
            })
