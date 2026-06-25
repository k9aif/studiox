# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9RetrievalAgent — OOB agent for RAG retrieval from VectorDB.

Takes a query from the payload, generates a query embedding via
EmbeddingServiceFactory, searches the VectorDB for top-k similar chunks,
and writes the retrieved context to the shared squad context.
Downstream reasoning agents use the retrieved context — not the raw document.
"""

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_data.vectordb_factory import VectorDBFactory
from k9_aif_abb.k9_factories.embedding_factory import EmbeddingServiceFactory


class K9RetrievalAgent(BaseAgent):

    layer = "RAG K9RetrievalAgent OOB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)
        self._vectordb = None
        self._embedding_svc = None
        self.top_k = self.config.get("top_k", 5)

    def _ensure_vectordb(self):
        if self._vectordb is None:
            self._vectordb = VectorDBFactory.from_config(self.config)

    def _ensure_embedding_svc(self):
        if self._embedding_svc is None:
            self._embedding_svc = EmbeddingServiceFactory.create(self.config)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = payload.get("query", "") or payload.get("question", "") or payload.get("prompt", "")

        if not query:
            self.logger.warning("[%s] No query in payload", self.layer)
            return {"agent": "K9RetrievalAgent", "retrieved": [], "count": 0, "error": "no query"}

        self._ensure_vectordb()
        self._ensure_embedding_svc()

        query_embedding = self._embedding_svc.embed(query)

        if not query_embedding:
            self.logger.error("[%s] Failed to generate query embedding", self.layer)
            return {"agent": "K9RetrievalAgent", "retrieved": [], "count": 0, "error": "embedding failed"}

        hits = self._vectordb.search(query_embedding, top_k=self.top_k)

        context_text = "\n\n---\n\n".join(h.get("text", "") for h in hits if h.get("text"))

        self.publish_event({"type": "RetrievalCompleted", "query": query[:100], "hits": len(hits)})
        self.logger.info("[%s] Retrieved %d chunks for query: %s", self.layer, len(hits), query[:80])

        return {
            "agent": "K9RetrievalAgent",
            "retrieved": hits,
            "count": len(hits),
            "context": context_text,
            "query": query,
        }
