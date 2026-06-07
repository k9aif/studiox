# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# K9-AIF - ChromaDB Persistence (SBB)
# Handles vector-based persistence for embeddings and similarity search.

import os
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from k9_aif_abb.k9_core.persistence.base_persistence import BasePersistence


class ChromaDBPersistence(BasePersistence):
    """
    SBB for vector storage and retrieval using ChromaDB.
    Provides insert and query methods with governance logging.
    """

    layer = "Persistence SBB"

    def __init__(self, config=None, monitor=None, **kwargs):
        super().__init__(config=config or {}, monitor=monitor, **kwargs)
        self.logger.info(f"[{self.layer}] Initializing ChromaDBPersistence")

        # ------------------------------------------------------------------
        # Path setup (create local persistent store)
        # ------------------------------------------------------------------
        base_path = (
            self.config.get("paths", {}).get("vector_store")
            or "./examples/acme_health_insurance/data/vector_store/.chroma"
        )
        os.makedirs(base_path, exist_ok=True)
        print(f"[ChromaDBPersistence]   Using base path: {base_path}")

        # Initialize Chroma persistent client
        self.client = chromadb.PersistentClient(
            path=base_path,
            settings=Settings(anonymized_telemetry=False)
        )
        print("[ChromaDBPersistence] [OK] Persistent client initialized")

        # Determine collection
        collection_name = (
            self.config.get("retriever", {})
            .get("sources", [{}])[0]
            .get("collection", "acme_health_knowledge")
        )
        print(f"[ChromaDBPersistence]  Target collection resolved: {collection_name}")

        self.collection = self.client.get_or_create_collection(collection_name)
        print(f"[ChromaDBPersistence]  Connected to Chroma collection: {collection_name}")

        # Optional config: embedding model (defaults to nomic-embed-text)
        self.embedding_model = (
            self.config.get("vectordb", {}).get("embedding_model", "nomic-embed-text")
        )

        self.logger.info(f"[{self.layer}] [OK] Connected to Chroma collection: {collection_name}")
        if monitor:
            monitor.log_event("chroma.init", {"collection": collection_name, "path": base_path})

    # ------------------------------------------------------------------
    def insert_embeddings(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
    ):
        """Insert document embeddings into ChromaDB."""
        print(f"[ChromaDBPersistence]  Inserting {len(ids)} documents...")
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadata,
        )
        print(f"[ChromaDBPersistence] [OK] Insert complete: {len(ids)} vectors added")
        if self.monitor:
            self.monitor.log_event("chroma.insert", {"count": len(ids)})

    # ------------------------------------------------------------------
    def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search using Ollama embedding model.
        Ensures embedding dimensions match those used during ingestion.
        """
        print(f"[ChromaDBPersistence]  Performing vector search -> query='{query}', top_k={top_k}")
        try:
            # --- Generate embedding via Ollama API (nomic-embed-text default)
            from ollama import Client
            client = Client(host="http://localhost:11434")
            model_name = self.embedding_model
            emb_data = client.embeddings(model=model_name, prompt=query)
            query_vector = emb_data.get("embedding")

            if not query_vector:
                print(f"[ChromaDBPersistence] [WARN] No embedding returned for query: {query}")
                return []

            # --- Execute the Chroma query
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )

            print(f"[ChromaDBPersistence]  Raw Chroma response keys: {list(results.keys())}")

            hits = []
            for doc, score, meta in zip(
                results.get("documents", [[]])[0],
                results.get("distances", [[]])[0],
                results.get("metadatas", [[]])[0],
            ):
                snippet = (doc[:100] + "...") if len(doc) > 100 else doc
                print(f"[ChromaDBPersistence] [INFO] Match: score={1 - score:.4f} | text='{snippet}'")
                hits.append({
                    "text": doc,
                    "score": 1 - score,  # convert distance -> similarity
                    "meta": meta,
                })

            print(f"[ChromaDBPersistence] [OK] {len(hits)} results found for query '{query}'")
            self.logger.info(f"[{self.layer}] Found {len(hits)} results for query.")
            if self.monitor:
                self.monitor.log_event("chroma.search", {"query": query, "hits": len(hits)})

            return hits

        except Exception as e:
            print(f"[ChromaDBPersistence] [ERROR] Vector search failed: {e}")
            self.logger.error(f"[{self.layer}] [ERROR] Vector search failed: {e}")
            return []

    # ----------------------------------------------------------------------
    # Abstract CRUD stubs (not applicable for Chroma vector store)
    # ----------------------------------------------------------------------
    def save_state(self, key: str, state: dict) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] save_state() not applicable for ChromaDB")

    def load_state(self, key: str):
        self.logger.debug(f"[{self.layer}:{self.name}] load_state() not applicable for ChromaDB")
        return None

    def update_state(self, key: str, state: dict) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] update_state() not applicable for ChromaDB")

    def delete_state(self, key: str) -> None:
        self.logger.debug(f"[{self.layer}:{self.name}] delete_state() not applicable for ChromaDB")