# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""BaseSessionStore — ABB contract for session storage backends."""

from abc import ABC, abstractmethod
from typing import List, Optional

from k9_aif_abb.k9_core.session.k9_session import K9Session


class BaseSessionStore(ABC):
    """
    Storage contract for K9Session persistence.

    SBBs implement this to provide the actual storage strategy:
    InMemorySessionStore, RedisSessionStore, SQLiteSessionStore, etc.
    """

    @abstractmethod
    def get(self, session_id: str) -> Optional[K9Session]:
        raise NotImplementedError

    @abstractmethod
    def save(self, session: K9Session) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: str) -> None:
        raise NotImplementedError

    def exists(self, session_id: str) -> bool:
        return self.get(session_id) is not None

    def list_active(self) -> List[K9Session]:
        return []
