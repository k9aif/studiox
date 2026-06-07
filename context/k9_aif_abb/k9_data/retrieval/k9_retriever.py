# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.retrieval.base_retriever import BaseRetriever


class K9Retriever(BaseRetriever):
    """
    Default framework retriever.

    Version 1:
      - reads source mappings from config
      - returns placeholder normalized results
      - later can call vector DB / APIs / hybrid search
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config=config)
        self.sources = self.config.get("sources", {})
        self.routing = self.config.get("routing", {})

    def retrieve(
        self,
        intent: str,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        filters = filters or {}

        source_names = self.routing.get(intent, {}).get("sources", [])

        results: List[Dict[str, Any]] = []
        for source_name in source_names[:top_k]:
            results.append(
                {
                    "text": f"Stub result for query='{query}' from source='{source_name}'",
                    "score": 1.0,
                    "source": source_name,
                    "metadata": {
                        "intent": intent,
                        "filters": filters,
                        "source_config": self.sources.get(source_name, {}),
                    },
                }
            )

        return results