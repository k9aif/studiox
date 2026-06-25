# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""K9Session — session data model."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DESTROYED = "destroyed"


class K9Session:
    """
    Represents one user session flowing through the K9-AIF execution hierarchy.

    session_id is auto-generated (UUID4) on construction — callers supply only
    user_id and optional metadata.
    """

    def __init__(
        self,
        user_id: str,
        ttl: int = 3600,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.session_id: str = str(uuid.uuid4())
        self.user_id: str = user_id
        self.created_at: datetime = datetime.utcnow()
        self.last_active: datetime = datetime.utcnow()
        self.ttl: int = ttl
        self.context: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = metadata or {}
        self.status: SessionStatus = SessionStatus.ACTIVE

    def touch(self) -> None:
        """Update last_active timestamp."""
        self.last_active = datetime.utcnow()

    def is_expired(self) -> bool:
        if self.status != SessionStatus.ACTIVE:
            return True
        elapsed = (datetime.utcnow() - self.last_active).total_seconds()
        return elapsed > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "ttl": self.ttl,
            "context": self.context,
            "metadata": self.metadata,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "K9Session":
        session = cls.__new__(cls)
        session.session_id = data["session_id"]
        session.user_id = data["user_id"]
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_active = datetime.fromisoformat(data["last_active"])
        session.ttl = data["ttl"]
        session.context = data.get("context", {})
        session.metadata = data.get("metadata", {})
        session.status = SessionStatus(data["status"])
        return session

    def __repr__(self) -> str:
        return (
            f"K9Session(session_id={self.session_id!r}, "
            f"user_id={self.user_id!r}, status={self.status.value!r})"
        )
