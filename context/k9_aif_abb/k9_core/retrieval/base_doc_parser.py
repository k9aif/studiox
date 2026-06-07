# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/parser/base_doc_parser.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseDocParser(BaseComponent, ABC):
    """
    K9-AIF Parser ABB - BaseDocParser
    ---------------------------------
    Abstract base interface for document parsers that transform
    unstructured inputs (PDF, DOCX, images) into structured JSON.

    Responsibilities:
    - Provide a unified async parse() contract for all parsers.
    - Integrate with BaseComponent for telemetry and observability.
    - Emit layer-aware logs visible in the live K9-AIF console.
    """

    layer = "Parser ABB"

    def __init__(self, name: Optional[str] = None, monitor=None):
        super().__init__(monitor=monitor)
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(message, level)
        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------
    @abstractmethod
    async def parse(self, content: bytes, **kwargs) -> Dict[str, Any]:
        """
        Parse raw document bytes and return structured data
        (e.g., extracted text, tables, metadata, annotations).
        """
        raise NotImplementedError