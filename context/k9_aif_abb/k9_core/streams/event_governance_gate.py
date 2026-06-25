# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""EventGovernanceGate — ABB contract for governing events at the fabric boundary."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope


class GateDecision(Enum):
    PERMIT = "PERMIT"   # event passes to agents unchanged
    REDACT = "REDACT"   # event passes with sensitive fields removed
    BLOCK  = "BLOCK"    # event stopped — agents never see it
    AUDIT  = "AUDIT"    # event passes but flagged for compliance logging


@dataclass
class GateResult:
    """Result of an EventGovernanceGate evaluation."""
    decision: GateDecision
    envelope: EventEnvelope
    reason:   Optional[str]      = None
    metadata: Dict[str, Any]     = field(default_factory=dict)


class EventGovernanceGate(ABC):
    """
    ABB contract for governing enterprise events before they reach agents.

    Every event entering the K9 context fabric MUST pass through a governance
    gate. Gates enforce:
      - PII detection and field-level redaction
      - Data sensitivity classification
      - Tenant-level access policies
      - Regulatory compliance (GDPR, HIPAA, SOX)

    BLOCKED events never reach agents, context windows, or projections.
    REDACTED events have sensitive fields removed before forwarding.

    This is the IBM value proposition made concrete in the framework:
    enterprise data streams are governed before AI systems consume them.

    SBBs: NoopGovernanceGate (dev/test), IBMOpenPagesGate (production)
    """

    @abstractmethod
    def evaluate(self, envelope: EventEnvelope) -> GateResult:
        """
        Evaluate an event envelope and return a gate decision.
        Must not raise — return BLOCK with a reason on errors.
        """
        raise NotImplementedError

    def is_permitted(self, envelope: EventEnvelope) -> bool:
        """Return True if the event is PERMIT, REDACT, or AUDIT (i.e. not BLOCK)."""
        result = self.evaluate(envelope)
        return result.decision in (GateDecision.PERMIT, GateDecision.REDACT, GateDecision.AUDIT)


class NoopGovernanceGate(EventGovernanceGate):
    """
    Passthrough gate — permits all events without inspection.
    For development and local testing only.

    In production, replace with a gate that enforces data governance policies.
    """

    def evaluate(self, envelope: EventEnvelope) -> GateResult:
        return GateResult(decision=GateDecision.PERMIT, envelope=envelope)
