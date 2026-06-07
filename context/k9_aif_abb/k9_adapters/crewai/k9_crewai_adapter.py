"""
Primary K9-AIF facade for CrewAI integration.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .crewai_orchestrator_adapter import CrewAIOrchestratorAdapter
from .crewai_payload_mapper import CrewAIPayloadMapper


class K9CrewAIAdapter:
    """
    OOB facade for integrating a CrewAI crew into K9-AIF.

    Responsibilities:
    - accept K9-AIF-style payloads
    - normalize payloads for CrewAI
    - invoke the wrapped CrewAI crew via adapter
    - normalize the response back to K9-AIF format
    """

    def __init__(
        self,
        crew: Any,
        mapper: Optional[CrewAIPayloadMapper] = None,
        orchestrator_adapter: Optional[CrewAIOrchestratorAdapter] = None,
    ) -> None:
        self.mapper = mapper or CrewAIPayloadMapper()
        self.orchestrator_adapter = orchestrator_adapter or CrewAIOrchestratorAdapter(crew=crew)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main adapter entrypoint for K9-AIF callers.
        """
        crew_input = self.mapper.to_crewai_input(payload)
        result = self.orchestrator_adapter.execute_flow(crew_input)
        return self.mapper.from_crewai_output(result)