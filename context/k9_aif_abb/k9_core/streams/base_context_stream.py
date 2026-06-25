# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""BaseContextStream — ABB contract for consuming a named enterprise data stream."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope


class BaseContextStream(ABC):
    """
    ABB contract for subscribing to a named enterprise data stream and
    projecting its events into agent-consumable context.

    A ContextStream represents one governed subscription to one enterprise
    source — e.g. "sap.policy.changes", "crm.customer.events", "iot.telemetry".

    The stream is read by the Orchestrator before squad execution to enrich
    the payload with live enterprise state. Agents never subscribe directly —
    they receive pre-fetched, pre-governed, pre-projected context.

    Subclasses implement:
      on_event(envelope)  — called for each arriving event
      project(envelope)   — transforms raw enterprise event into agent dict
    """

    stream_id:     str = ""
    source_system: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._context: Dict[str, Any] = {}

    @abstractmethod
    def on_event(self, envelope: EventEnvelope) -> None:
        """
        Called for each event arriving on this stream.
        Implementations should call project() and update self._context.
        """
        raise NotImplementedError

    @abstractmethod
    def project(self, envelope: EventEnvelope) -> Dict[str, Any]:
        """
        Transform a raw enterprise event into an agent-consumable context dict.

        Agents speak domain language, not source-system schema.
        Example: SAP policy.updated → {"policy_id": ..., "coverage": ..., "effective_date": ...}
        """
        raise NotImplementedError

    def get_context(self) -> Dict[str, Any]:
        """Return the current projected context snapshot from this stream."""
        return dict(self._context)

    def reset(self) -> None:
        """Clear accumulated context — useful between test runs."""
        self._context.clear()
