# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker


class SQLiteDatabaseStorage:
    """
    OOB SQLite relational storage for K9 Model Router session state.

    Responsibilities:
    - provide SQLAlchemy engine
    - provide shared metadata object
    - create SQLite DB file if missing
    - expose session factory for RoutingStateStore
    """

    def __init__(self, db_path: str = "./runtime/k9_model_router.db", monitor=None):
        self.db_path = Path(db_path)
        self.monitor = monitor

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        db_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(db_url, future=True)
        self.metadata = MetaData()
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def get_session(self):
        return self.SessionLocal()

    def close(self):
        if self.engine:
            self.engine.dispose()