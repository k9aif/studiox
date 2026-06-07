"""
Base adapter contract for K9-AIF.

Adapters bridge external frameworks, runtimes, or protocols
into K9-AIF architectural contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAdapter(ABC):
    """
    Abstract base class for all K9-AIF adapters.
    """

    def __init__(
        self,
        adapter_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.adapter_name = adapter_name or self.__class__.__name__
        self.metadata = metadata or {}

    def validate_payload(self, payload: Dict[str, Any]) -> None:
        """Optional validation hook for inbound payloads."""
        return None

    @abstractmethod
    def adapt_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Translate inbound K9-AIF payload into external-runtime-friendly form."""

    @abstractmethod
    def adapt_output(self, result: Any) -> Dict[str, Any]:
        """Translate external runtime output back into K9-AIF-friendly form."""

    def get_adapter_metadata(self) -> Dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "metadata": self.metadata,
        }