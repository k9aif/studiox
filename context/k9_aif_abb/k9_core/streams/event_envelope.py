# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""EventEnvelope — standard wrapper for all events in the K9 enterprise context fabric."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class EventEnvelope:
    """
    Universal event wrapper for all events flowing through the K9 enterprise context fabric.

    Every event — SAP change, CRM update, CDC record, IoT telemetry, agent result —
    is wrapped in an EventEnvelope before being published or consumed.

    Fields:
        event_type      Routing key, e.g. "sap.policy.updated", "crm.customer.changed"
        source_system   Originating system, e.g. "sap", "salesforce", "claims-db"
        payload         The actual event data (domain-specific dict)
        event_id        Auto-generated UUID — unique per event
        correlation_id  Client-supplied or auto-generated; links related events
        causation_id    Parent event_id — tracks causal chains across agents
        schema_version  Payload schema version for projection compatibility
        timestamp       UTC time of event creation
        metadata        Routing hints, sensitivity classification, tenant context
    """

    event_type:     str
    source_system:  str
    payload:        Dict[str, Any]

    event_id:       str            = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str]  = field(default=None)
    causation_id:   Optional[str]  = field(default=None)
    schema_version: str            = field(default="1.0")
    timestamp:      datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type,
            "source_system":  self.source_system,
            "payload":        self.payload,
            "correlation_id": self.correlation_id,
            "causation_id":   self.causation_id,
            "schema_version": self.schema_version,
            "timestamp":      self.timestamp.isoformat(),
            "metadata":       self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventEnvelope":
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            event_type=data["event_type"],
            source_system=data["source_system"],
            payload=data.get("payload", {}),
            event_id=data.get("event_id", str(uuid.uuid4())),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            schema_version=data.get("schema_version", "1.0"),
            timestamp=ts or datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )
