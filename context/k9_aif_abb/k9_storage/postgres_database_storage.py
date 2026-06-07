# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from sqlalchemy import MetaData, Table, and_, create_engine, delete, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from k9_aif_abb.k9_storage.database_storage import BaseDatabaseStorage


class PostgresDatabaseStorage(BaseDatabaseStorage):
    """
    OOB PostgreSQL Database Storage SBB
    ----------------------------------
    Reusable PostgreSQL-backed implementation of the BaseDatabaseStorage ABB.

    Responsibilities:
    - Read PostgreSQL config
    - Create engine and session factory
    - Support schema-aware connections
    - Provide generic CRUD helpers
    - Provide context-managed transactional sessions
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None):
        super().__init__(config=config, monitor=monitor)

        pg = (self.config or {}).get("postgres", {})

        self.host = pg.get("host", "localhost")
        self.port = pg.get("port", 5432)
        self.user = pg.get("user", "postgres")
        self.password = pg.get("password", "postgres")
        self.database = pg.get("database", "postgres")
        self.schema = pg.get("schema", "public")
        self.echo = bool(pg.get("echo", False))

        self.database_url = (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.metadata = MetaData(schema=self.schema)

        self.connect()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        if self.engine is not None and self.SessionLocal is not None:
            return

        connect_args: Dict[str, Any] = {}
        if self.schema and self.schema != "public":
            connect_args["options"] = f"-c search_path={self.schema}"

        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
            echo=self.echo,
            future=True,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self.SessionLocal = None

    # ------------------------------------------------------------------
    # Transaction / Session
    # ------------------------------------------------------------------
    @contextmanager
    def begin(self):
        if self.SessionLocal is None:
            raise RuntimeError("PostgresDatabaseStorage is not connected")

        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Session Access (required by RoutingStateStore)
    # ------------------------------------------------------------------
    @contextmanager
    def get_session(self):
        """
        Provide a simple session context (same contract as SQLite backend).
        """
        if self.SessionLocal is None:
            raise RuntimeError("PostgresDatabaseStorage is not connected")

        session: Session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    def _get_table(self, table: str) -> Table:
        if self.engine is None:
            raise RuntimeError("PostgresDatabaseStorage is not connected")

        return Table(table, self.metadata, autoload_with=self.engine)

    @staticmethod
    def _build_where_clause(tbl: Table, filters: Dict[str, Any]):
        if not filters:
            return None
        clauses = [tbl.c[key] == value for key, value in filters.items()]
        return and_(*clauses)

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------
    def insert(self, table: str, record: Dict[str, Any]) -> Any:
        tbl = self._get_table(table)

        with self.begin() as session:
            stmt = insert(tbl).values(**record)
            result = session.execute(stmt)
            return result.rowcount

    def query(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        tbl = self._get_table(table)

        stmt = select(tbl)
        where_clause = self._build_where_clause(tbl, filters)
        if where_clause is not None:
            stmt = stmt.where(where_clause)

        with self.begin() as session:
            rows = session.execute(stmt).fetchall()
            return [dict(row._mapping) for row in rows]

    def update(self, table: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> Any:
        tbl = self._get_table(table)

        stmt = update(tbl).values(**updates)
        where_clause = self._build_where_clause(tbl, filters)
        if where_clause is not None:
            stmt = stmt.where(where_clause)

        with self.begin() as session:
            result = session.execute(stmt)
            return result.rowcount

    def delete(self, table: str, filters: Dict[str, Any]) -> Any:
        tbl = self._get_table(table)

        stmt = delete(tbl)
        where_clause = self._build_where_clause(tbl, filters)
        if where_clause is not None:
            stmt = stmt.where(where_clause)

        with self.begin() as session:
            result = session.execute(stmt)
            return result.rowcount

    # ------------------------------------------------------------------
    # Optional Execution Helper
    # ------------------------------------------------------------------
    def execute(self, statement: Any) -> Any:
        with self.begin() as session:
            return session.execute(statement)