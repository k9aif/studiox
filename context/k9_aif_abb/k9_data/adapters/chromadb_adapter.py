# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""ChromaDB adapter for BaseVectorDB — config-driven, lazy imports."""

import os
from typing import Any, Dict, List

from k9_aif_abb.k9_data.base_vectordb import BaseVectorDB


class ChromaDBAdapter(BaseVectorDB):
    """
    SBB: ChromaDB vector store adapter.
    Extends BaseVectorDB with ChromaDB-specific implementation.
    Uses lazy imports — chromadb is not required unless this adapter is used.
    """

    layer = "Data SBB"

    def __init__(self, config=None, monitor=None):
        super().__init__(name="ChromaDBAdapter", monitor=monitor)
        self._config = config or {}
        self._client = None
        self._collection = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise RuntimeError("pip install chromadb required for ChromaDBAdapter") from exc

        vdb_cfg = self._config.get("vectordb", {})
        base_path = vdb_cfg.get("path", os.environ.get("CHROMA_PATH", "./.chroma"))
        os.makedirs(base_path, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=base_path,
            settings=Settings(anonymized_telemetry=False),
        )

        collection_name = vdb_cfg.get("collection", "k9_default")
        self._collection = self._client.get_or_create_collection(collection_name)
        self.logger.info("[%s] Connected to ChromaDB collection: %s at %s", self.layer, collection_name, base_path)

    def insert(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        self._ensure_client()
        self._collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[metadata.get("text", "")],
        )

    def insert_batch(self, ids: List[str], embeddings: List[List[float]],
                     documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        self._ensure_client()
        self._collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        self._ensure_client()
        results = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
        hits = []
        for doc, score, meta in zip(
            results.get("documents", [[]])[0],
            results.get("distances", [[]])[0],
            results.get("metadatas", [[]])[0],
        ):
            hits.append({"text": doc, "score": 1 - score, "metadata": meta})
        return hits

    def delete(self, doc_id: str) -> None:
        self._ensure_client()
        self._collection.delete(ids=[doc_id])

    def count(self) -> int:
        self._ensure_client()
        return self._collection.count()
