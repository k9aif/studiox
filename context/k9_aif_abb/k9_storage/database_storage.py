# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseDatabaseStorage(ABC):
    """
    ABB Contract: BaseDatabaseStorage
    --------------------------------
    Defines the abstract contract for structured database storage backends.

    OOB SBBs such as PostgreSQL, SQLite, or future enterprise DB providers
    should extend this class.

    This class intentionally avoids embedding database-specific logic.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None):
        self.config = config or {}
        self.monitor = monitor

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @abstractmethod
    def connect(self) -> None:
        """Initialize or validate the database connection."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close any open database resources."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------
    @abstractmethod
    def insert(self, table: str, record: Dict[str, Any]) -> Any:
        """
        Insert a record into a table.

        Returns:
            Backend-specific insert result or identifier.
        """
        raise NotImplementedError

    @abstractmethod
    def query(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query records from a table matching the provided filters.
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, table: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> Any:
        """
        Update records in a table matching filters.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, table: str, filters: Dict[str, Any]) -> Any:
        """
        Delete records in a table matching filters.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Optional Execution Helpers
    # ------------------------------------------------------------------
    def execute(self, statement: Any) -> Any:
        """
        Optional backend-specific execution helper.

        Subclasses may override this if they support raw SQLAlchemy
        statements or native SQL execution.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement execute()"
        )

    def begin(self):
        """
        Optional transaction/session context manager.

        Subclasses may override to provide a context-managed DB session.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement begin()"
        )