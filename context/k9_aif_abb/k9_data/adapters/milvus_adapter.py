# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""Milvus adapter for BaseVectorDB — config-driven, lazy imports."""

from typing import Any, Dict, List

from k9_aif_abb.k9_data.base_vectordb import BaseVectorDB


class MilvusAdapter(BaseVectorDB):
    """
    SBB: Milvus vector store adapter.
    Extends BaseVectorDB with Milvus-specific implementation.
    Uses lazy imports — pymilvus is not required unless this adapter is used.
    """

    layer = "Data SBB"

    def __init__(self, config=None, monitor=None):
        super().__init__(name="MilvusAdapter", monitor=monitor)
        self._config = config or {}
        self._client = None
        self._collection = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from pymilvus import MilvusClient
        except ImportError as exc:
            raise RuntimeError("pip install pymilvus required for MilvusAdapter") from exc

        vdb_cfg = self._config.get("vectordb", {})
        uri = vdb_cfg.get("uri", "http://localhost:19530")
        collection_name = vdb_cfg.get("collection", "k9_default")
        dimension = vdb_cfg.get("dimension", 768)

        self._client = MilvusClient(uri=uri)
        self._collection_name = collection_name
        self._dimension = dimension

        if not self._client.has_collection(collection_name):
            self._client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
            )

        self.logger.info("[%s] Connected to Milvus collection: %s at %s", self.layer, collection_name, uri)

    def insert(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        self._ensure_client()
        self._client.insert(
            collection_name=self._collection_name,
            data=[{"id": doc_id, "vector": embedding, **metadata}],
        )

    def insert_batch(self, ids: List[str], embeddings: List[List[float]],
                     documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        self._ensure_client()
        data = []
        for i, (doc_id, emb, doc, meta) in enumerate(zip(ids, embeddings, documents, metadatas)):
            entry = {"id": doc_id, "vector": emb, "text": doc}
            entry.update(meta)
            data.append(entry)
        self._client.insert(collection_name=self._collection_name, data=data)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        self._ensure_client()
        results = self._client.search(
            collection_name=self._collection_name,
            data=[query_embedding],
            limit=top_k,
            output_fields=["text"],
        )
        hits = []
        for hit in results[0]:
            hits.append({
                "text": hit.get("entity", {}).get("text", ""),
                "score": hit.get("distance", 0),
                "metadata": {"id": hit.get("id")},
            })
        return hits

    def delete(self, doc_id: str) -> None:
        self._ensure_client()
        self._client.delete(collection_name=self._collection_name, ids=[doc_id])

    def count(self) -> int:
        self._ensure_client()
        stats = self._client.get_collection_stats(self._collection_name)
        return stats.get("row_count", 0)
