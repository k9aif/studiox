# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/supporting/processor_agent.py

from typing import Dict, Any
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_factories.llm_factory import LLMFactory


class ProcessorAgent(BaseAgent):
    """
    K9-AIF ProcessorAgent
    ---------------------
    ABB-level component responsible for transforming or synthesizing
    retrieved content into a final response.

    Responsibilities:
    - Combine retrieved documents or structured inputs
    - Optionally call LLMFactory-provisioned models for synthesis
    - Produce structured responses for downstream UI or storage
    """

    layer = "Processor ABB"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config or {}, name="ProcessorAgent")

        # Optional LLM synthesizer
        llm_cfg = self.config.get("processor", {}).get("llm")
        self.llm = LLMFactory.from_config(llm_cfg) if llm_cfg else None
        if self.llm:
            self.log(f"[{self.layer}] Initialized with LLM backend: {type(self.llm).__name__}")
        else:
            self.log(f"[{self.layer}] No LLM backend configured - running in stub mode", "WARN")

    def execute(self, request: dict) -> dict:
        """
        Process retrieved content and optionally generate an answer via LLM.
        Supports flexible input schemas (handles both 'text' and 'query').
        """
        # Safely normalize query text
        query = request.get("query") or request.get("text") or "unknown"
        docs = request.get("retrieved_docs", [])
        self.log(f"[{self.layer}] Processing query='{query}' with {len(docs)} retrieved docs")

        # --- Option A: LLM synthesis ---
        if self.llm:
            context = "\n".join(docs) if docs else "(no retrieved context)"
            prompt = f"Answer the query based on context:\n{context}\n\nQuery: {query}"
            try:
                response = str(self.llm.generate(prompt))
                self.log(f"[{self.layer}] LLM synthesis successful", "INFO")
            except Exception as e:
                response = f"[ProcessorAgent] LLM generation failed: {e}"
                self.log(response, "ERROR")

            return {
                "answer": response,
                "query": query,
                "docs": docs,
                "llm_used": self.llm.__class__.__name__,
            }

        # --- Option B: Stubbed fallback ---
        self.log(f"[{self.layer}] No LLM configured - returning stubbed response", "WARN")
        return {
            "answer": f"Stubbed answer for query: {query}",
            "query": query,
            "docs": docs,
            "llm_used": "none",
        }