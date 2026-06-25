# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9DocPreprocessor — OOB agent for document chunking and structure extraction.

Reads a raw document from the payload, splits it into chunks respecting
section boundaries, and writes structured chunks to the shared context.
Downstream agents read chunks — not the raw document.
"""

import re
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class K9DocPreprocessor(BaseAgent):

    layer = "RAG K9DocPreprocessor OOB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)
        self.max_chunk_tokens = self.config.get("max_chunk_tokens", 1000)
        self.overlap_tokens = self.config.get("overlap_tokens", 100)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        document = payload.get("document", "") or payload.get("text", "") or payload.get("content", "")

        if not document:
            self.logger.warning("[%s] No document found in payload", self.layer)
            return {"agent": "K9DocPreprocessor", "chunks": [], "chunk_count": 0, "error": "no document in payload"}

        sections = self._extract_sections(document)
        chunks = self._chunk_sections(sections)

        self.publish_event({"type": "DocumentPreprocessed", "chunk_count": len(chunks)})
        self.logger.info("[%s] Preprocessed document into %d chunks", self.layer, len(chunks))

        return {
            "agent": "K9DocPreprocessor",
            "chunks": chunks,
            "chunk_count": len(chunks),
            "metadata": {
                "total_chars": len(document),
                "section_count": len(sections),
                "max_chunk_tokens": self.max_chunk_tokens,
            },
        }

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        header_pattern = re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE)
        matches = list(header_pattern.finditer(text))

        if not matches:
            return [{"title": "Document", "level": 0, "content": text.strip()}]

        sections = []
        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if content:
                sections.append({"title": title, "level": level, "content": content})

        return sections

    def _chunk_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        for section in sections:
            content = section["content"]
            words = content.split()
            if len(words) <= self.max_chunk_tokens:
                chunks.append({
                    "text": content,
                    "section": section["title"],
                    "index": len(chunks),
                    "token_estimate": len(words),
                })
            else:
                start = 0
                while start < len(words):
                    end = min(start + self.max_chunk_tokens, len(words))
                    chunk_words = words[start:end]
                    chunks.append({
                        "text": " ".join(chunk_words),
                        "section": section["title"],
                        "index": len(chunks),
                        "token_estimate": len(chunk_words),
                    })
                    start = end - self.overlap_tokens if end < len(words) else end

        return chunks
