"""
Payload mapping utilities for adapting K9-AIF payloads to CrewAI-friendly inputs.
"""

from __future__ import annotations

from typing import Any, Dict


class CrewAIPayloadMapper:
    """Translate K9-AIF payloads into normalized CrewAI inputs."""

    def to_crewai_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize incoming K9-AIF payload into a structure suitable for CrewAI.

        Expected flexible input examples:
        - {"message": "...", "intent": "support"}
        - {"input": "..."}
        - {"query": "...", "context": {...}}
        """
        payload = payload or {}

        message = (
            payload.get("message")
            or payload.get("input")
            or payload.get("query")
            or ""
        )

        return {
            "message": message,
            "intent": payload.get("intent"),
            "context": payload.get("context", {}),
            "metadata": payload.get("metadata", {}),
            "raw_payload": payload,
        }

    def from_crewai_output(self, result: Any) -> Dict[str, Any]:
        """
        Normalize CrewAI output back into a K9-AIF-friendly response envelope.
        """
        if isinstance(result, dict):
            return {
                "status": "success",
                "result": result,
                "output_text": result.get("output") or result.get("message") or str(result),
            }

        return {
            "status": "success",
            "result": result,
            "output_text": str(result),
        }