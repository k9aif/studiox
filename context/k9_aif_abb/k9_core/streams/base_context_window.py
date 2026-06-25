# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""BaseContextWindow — ABB contract for temporal enterprise event memory."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.streams.event_envelope import EventEnvelope


class BaseContextWindow(ABC):
    """
    ABB contract for maintaining a temporal window of enterprise events.

    Gives agents temporal awareness — not just the current state of the
    enterprise, but the sequence of events leading to it.

    Example: "What changed on policy P001 in the last 24 hours?"
    answers the question a ClaimsAgent needs before adjudicating a claim.

    Queried by the Orchestrator before squad execution; context injected
    into the payload so agents receive temporal grounding without managing
    stream subscriptions themselves.

    SBBs: InMemoryContextWindow (local/test), RedisContextWindow (distributed)

    YAML config::

        streams:
          window:
            max_events:  500    # max events retained (default 500)
            ttl_seconds: 86400  # event TTL in seconds (default 24h)
    """

    @abstractmethod
    def add(self, envelope: EventEnvelope) -> None:
        """Add an event envelope to the window."""
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        event_type:     Optional[str]      = None,
        source_system:  Optional[str]      = None,
        since:          Optional[datetime] = None,
        correlation_id: Optional[str]      = None,
        limit:          Optional[int]      = None,
    ) -> List[EventEnvelope]:
        """
        Query events in the window by filter criteria.
        Returns matching envelopes in chronological order.
        """
        raise NotImplementedError

    @abstractmethod
    def snapshot(self) -> Dict[str, Any]:
        """
        Return a summary snapshot of current window state.
        Used by Orchestrator to inject temporal context into agent payload.
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all events from the window."""
        raise NotImplementedError

    def size(self) -> int:
        """Number of events currently in the window."""
        return len(self.query())
