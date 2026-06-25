# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""BaseContextProjection — ABB contract for transforming enterprise events into agent context."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope


class BaseContextProjection(ABC):
    """
    ABB contract for transforming raw enterprise events into agent-usable context.

    A projection is a declarative mapping: source-system schema → agent vocabulary.
    Agents speak domain terms, not SAP IDoc or Salesforce API formats.

    Multiple projections can be registered per stream. The first projection
    whose accepts() returns True is applied.

    Example:
        SAP event:  {"VBELN": "P001", "KBETR": 5000.00, "WAERS": "USD"}
        Projected:  {"policy_id": "P001", "premium": 5000.00, "currency": "USD"}

    SBBs implement one projection per source-system event type.
    """

    @abstractmethod
    def accepts(self, envelope: EventEnvelope) -> bool:
        """
        Return True if this projection handles the given event.
        Called before project() to determine applicability.
        """
        raise NotImplementedError

    @abstractmethod
    def project(self, envelope: EventEnvelope) -> Dict[str, Any]:
        """
        Transform the event envelope payload into an agent-consumable dict.
        Must not raise — return {} if the projection cannot be applied.
        """
        raise NotImplementedError
