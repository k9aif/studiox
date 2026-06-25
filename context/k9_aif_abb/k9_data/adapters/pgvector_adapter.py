# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""pgvector adapter for BaseVectorDB — config-driven, lazy imports."""

import json
import os
from typing import Any, Dict, List

from k9_aif_abb.k9_data.base_vectordb import BaseVectorDB


class PgVectorAdapter(BaseVectorDB):
    """
    SBB: PostgreSQL + pgvector adapter.
    Extends BaseVectorDB with pgvector-specific implementation.
    Uses lazy imports — psycopg2 and pgvector are not required unless this adapter is used.
    """

    layer = "Data SBB"

    def __init__(self, config=None, monitor=None):
        super().__init__(name="PgVectorAdapter", monitor=monitor)
        self._config = config or {}
        self._conn = None
        self._table = None

    def _ensure_client(self):
        if self._conn is not None:
            return
        try:
            import psycopg2
            from psycopg2.extras import Json
        except ImportError as exc:
            raise RuntimeError("pip install psycopg2-binary required for PgVectorAdapter") from exc

        vdb_cfg = self._config.get("vectordb", {})
        pg_cfg = self._config.get("postgres", {})

        host = vdb_cfg.get("host", pg_cfg.get("host", os.environ.get("POSTGRES_HOST", "localhost")))
        port = vdb_cfg.get("port", pg_cfg.get("port", "5432"))
        dbname = vdb_cfg.get("dbname", pg_cfg.get("database", os.environ.get("POSTGRES_DB", "k9x")))
        user = vdb_cfg.get("user", pg_cfg.get("user", os.environ.get("POSTGRES_USER", "postgres")))
        password = vdb_cfg.get("password", pg_cfg.get("password", os.environ.get("POSTGRES_PASSWORD", "")))
        self._table = vdb_cfg.get("table", "k9_vectors")
        dimension = vdb_cfg.get("dimension", 768)

        self._conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        self._conn.autocommit = True

        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    embedding vector({dimension}),
                    document TEXT,
                    metadata JSONB
                )
            """)

        self.logger.info("[%s] Connected to pgvector table: %s at %s:%s/%s", self.layer, self._table, host, port, dbname)

    def insert(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        self._ensure_client()
        with self._conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self._table} (id, embedding, document, metadata) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, document = EXCLUDED.document, metadata = EXCLUDED.metadata",
                (doc_id, str(embedding), metadata.get("text", ""), json.dumps(metadata)),
            )

    def insert_batch(self, ids: List[str], embeddings: List[List[float]],
                     documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        self._ensure_client()
        with self._conn.cursor() as cur:
            for doc_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
                cur.execute(
                    f"INSERT INTO {self._table} (id, embedding, document, metadata) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, document = EXCLUDED.document, metadata = EXCLUDED.metadata",
                    (doc_id, str(emb), doc, json.dumps(meta)),
                )

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        self._ensure_client()
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT id, document, metadata, embedding <=> %s::vector AS distance FROM {self._table} ORDER BY distance LIMIT %s",
                (str(query_embedding), top_k),
            )
            rows = cur.fetchall()
        return [
            {"text": row[1], "score": 1 - row[3], "metadata": row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")}
            for row in rows
        ]

    def delete(self, doc_id: str) -> None:
        self._ensure_client()
        with self._conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._table} WHERE id = %s", (doc_id,))

    def count(self) -> int:
        self._ensure_client()
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._table}")
            return cur.fetchone()[0]
