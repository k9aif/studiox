# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""Qdrant adapter for BaseVectorDB — config-driven, lazy imports."""

import uuid
from typing import Any, Dict, List

from k9_aif_abb.k9_data.base_vectordb import BaseVectorDB


class QdrantAdapter(BaseVectorDB):
    """
    SBB: Qdrant vector store adapter.
    Extends BaseVectorDB with Qdrant-specific implementation.
    Uses lazy imports — qdrant-client is not required unless this adapter is used.
    """

    layer = "Data SBB"

    def __init__(self, config=None, monitor=None):
        super().__init__(name="QdrantAdapter", monitor=monitor)
        self._config = config or {}
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise RuntimeError("pip install qdrant-client required for QdrantAdapter") from exc

        vdb_cfg = self._config.get("vectordb", {})
        url = vdb_cfg.get("url", "http://localhost:6333")
        self._collection_name = vdb_cfg.get("collection", "k9_default")
        dimension = vdb_cfg.get("dimension", 768)

        self._client = QdrantClient(url=url)

        collections = [c.name for c in self._client.get_collections().collections]
        if self._collection_name not in collections:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

        self.logger.info("[%s] Connected to Qdrant collection: %s at %s", self.layer, self._collection_name, url)

    def insert(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        self._ensure_client()
        from qdrant_client.models import PointStruct
        point = PointStruct(id=doc_id, vector=embedding, payload=metadata)
        self._client.upsert(collection_name=self._collection_name, points=[point])

    def insert_batch(self, ids: List[str], embeddings: List[List[float]],
                     documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        self._ensure_client()
        from qdrant_client.models import PointStruct
        points = []
        for doc_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            payload = {**meta, "text": doc}
            points.append(PointStruct(id=doc_id, vector=emb, payload=payload))
        self._client.upsert(collection_name=self._collection_name, points=points)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        self._ensure_client()
        results = self._client.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            limit=top_k,
        )
        return [
            {"text": hit.payload.get("text", ""), "score": hit.score, "metadata": hit.payload}
            for hit in results
        ]

    def delete(self, doc_id: str) -> None:
        self._ensure_client()
        self._client.delete(collection_name=self._collection_name, points_selector=[doc_id])

    def count(self) -> int:
        self._ensure_client()
        info = self._client.get_collection(self._collection_name)
        return info.points_count
