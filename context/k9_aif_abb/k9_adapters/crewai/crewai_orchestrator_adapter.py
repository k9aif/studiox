from __future__ import annotations

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.base_adapter import BaseAdapter
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator


class CrewAIOrchestratorAdapter(BaseOrchestrator, BaseAdapter):
    """
    Adapter that wraps a CrewAI Crew and exposes it through K9-AIF orchestration contracts.
    """

    def __init__(self, crew: Any, name: Optional[str] = None) -> None:
        BaseAdapter.__init__(self, adapter_name=name or "CrewAIOrchestratorAdapter")
        BaseOrchestrator.__init__(self)
        self.crew = crew

    def adapt_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    def adapt_output(self, result: Any) -> Dict[str, Any]:
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

    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_payload(payload)
        crew_input = self.adapt_input(payload)

        if hasattr(self.crew, "kickoff"):
            result = self.crew.kickoff(inputs=crew_input)
        elif hasattr(self.crew, "run"):
            result = self.crew.run(crew_input)
        else:
            raise AttributeError(
                "Provided CrewAI crew does not support kickoff() or run()."
            )

        return self.adapt_output(result)