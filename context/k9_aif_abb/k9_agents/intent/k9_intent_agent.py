# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9IntentAgent — OOB LLM-driven intent classification agent.

Analogous to ``K9ValidationLoopAgent`` and ``K9ModelRouter``:
ready-to-use out of the box, configurable entirely via YAML,
and designed to be extended with minimal code.

Classification order
--------------------
1. ``intent_map`` config dict  — deterministic, zero-latency rule lookup
2. ``llm_invoke``              — LLM prompt-based classification
3. ``fallback_intent()``       — event_type verbatim, or ``"unknown"``

YAML configuration
------------------
Wire via agent YAML (``class: K9IntentAgent``) with these optional keys::

    intent_map:                   # rule-based fast-path (checked first)
      claim_submitted: claims
      fraud_alert:     fraud
      doc_uploaded:    document_processing

    intent_field: event_type      # payload key to read (default: event_type)

    llm_prompt_tmpl: |            # {payload} is substituted at runtime
      You are an intent classifier for an insurance operations system.
      Given the event payload below, respond with one lowercase intent label.
      Valid intents: claims, fraud, document_processing, compliance, unknown.

      Payload: {payload}

      Intent:

    model: general                # model alias for K9ModelRouter scoring

SBB extension
-------------
Override only what differs::

    class InsuranceIntentAgent(K9IntentAgent):
        layer = "InsuranceIntentAgent SBB"

        def normalize_intent(self, raw):
            # map any LLM variation to canonical domain labels
            mapping = {"claim": "claims", "fraud_signal": "fraud"}
            clean = super().normalize_intent(raw)
            return mapping.get(clean, clean)
"""

import logging
from typing import Any, Dict, Optional

from k9_aif_abb.k9_agents.intent.base_intent_agent import BaseIntentAgent
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke

log = logging.getLogger(__name__)

_DEFAULT_PROMPT = (
    "You are an intent classifier for a multi-agent system.\n"
    "Given the following event payload, respond with a single intent label "
    "(lowercase, underscores only, no spaces, no punctuation).\n\n"
    "Payload: {payload}\n\n"
    "Intent:"
)


class K9IntentAgent(BaseIntentAgent):
    """
    OOB LLM-driven intent classification agent.

    Use directly via YAML (``class: K9IntentAgent``) for zero-code intent
    classification, or extend and override ``classify()`` / ``normalize_intent()``
    for domain-specific logic.
    """

    layer = "K9IntentAgent"

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
        self.intent_map: Dict[str, str] = self.config.get("intent_map", {})
        self.intent_field: str = self.config.get("intent_field", "event_type")
        self.prompt_tmpl: str = self.config.get("llm_prompt_tmpl", _DEFAULT_PROMPT)

    def classify(self, payload: Dict[str, Any]) -> str:
        event_type = str(payload.get(self.intent_field, ""))

        # 1. Rule-based fast-path
        if event_type in self.intent_map:
            mapped = self.intent_map[event_type]
            log.info("[%s] rule-based: event_type=%s → intent=%s", self.layer, event_type, mapped)
            return mapped

        # 2. LLM classification
        prompt = self.prompt_tmpl.format(payload=payload)
        req = InferenceRequest(
            prompt=prompt,
            task_type=self.config.get("model", "general"),
            metadata={"agent": self.layer},
        )
        resp = llm_invoke(self.config, req)
        log.info("[%s] llm classified raw=%r model=%s", self.layer, resp.output, resp.model_alias)
        return resp.output
