# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9EmbeddingAgent — OOB agent for generating embeddings and storing in VectorDB.

Reads chunks from the shared context (produced by K9DocPreprocessor),
generates embeddings via EmbeddingServiceFactory, and stores
them in the VectorDB via VectorDBFactory.
"""

import hashlib
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_data.vectordb_factory import VectorDBFactory
from k9_aif_abb.k9_factories.embedding_factory import EmbeddingServiceFactory


class K9EmbeddingAgent(BaseAgent):

    layer = "RAG K9EmbeddingAgent OOB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)
        self._vectordb = None
        self._embedding_svc = None

    def _ensure_vectordb(self):
        if self._vectordb is None:
            self._vectordb = VectorDBFactory.from_config(self.config)

    def _ensure_embedding_svc(self):
        if self._embedding_svc is None:
            self._embedding_svc = EmbeddingServiceFactory.create(self.config)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        chunks = payload.get("chunks", [])

        if not chunks:
            self.logger.warning("[%s] No chunks in payload", self.layer)
            return {"agent": "K9EmbeddingAgent", "indexed": 0, "error": "no chunks"}

        self._ensure_vectordb()
        self._ensure_embedding_svc()

        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            text = chunk.get("text", "")
            if not text:
                continue

            doc_id = hashlib.md5(text.encode()).hexdigest()
            embedding = self._embedding_svc.embed(text)

            if not embedding:
                self.logger.warning("[%s] Empty embedding for chunk %s", self.layer, chunk.get("index"))
                continue

            ids.append(doc_id)
            embeddings.append(embedding)
            documents.append(text)
            metadatas.append({
                "section": chunk.get("section", ""),
                "index": chunk.get("index", 0),
            })

        if ids:
            self._vectordb.insert_batch(ids, embeddings, documents, metadatas)

        self.publish_event({"type": "EmbeddingsGenerated", "count": len(ids)})
        self.logger.info("[%s] Indexed %d chunks into VectorDB", self.layer, len(ids))

        return {
            "agent": "K9EmbeddingAgent",
            "indexed": len(ids),
            "skipped": len(chunks) - len(ids),
        }
