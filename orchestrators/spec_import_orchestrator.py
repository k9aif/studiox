# SPDX-License-Identifier: Apache-2.0
# k9x_studio — SpecImportOrchestrator (SBB)
#
# Coordinates SpecImportSquad for the "spec_import" event. Knows only its
# squad — loaded by YAML file and id through the squad layer
# (router_factory.py builds it) — never its agents, the router or other
# orchestrators (Squad Layer pattern, k9aif inspect K9-DEC-002).

from pathlib import Path
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator

_SQUAD_ID = "SpecImportSquad"
_SQUAD_YAML = Path(__file__).resolve().parent.parent / "squads" / "yaml" / "spec_import_squad.yaml"


class SpecImportOrchestrator(BaseOrchestrator):

    layer = "k9x_studio SpecImportOrchestrator SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, squads=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, squads=squads, **kwargs)
        self._squad = self.squads.load_one(_SQUAD_YAML, _SQUAD_ID)

    # ------------------------------------------------------------------
    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self._squad.execute(payload)

        governance = result.get("governance", {})
        if not governance.get("passed", True):
            self.publish_status("FlowBlocked", {
                "squad_id": _SQUAD_ID,
                "correlation_id": payload.get("correlation_id"),
                "reason": governance.get("reason"),
            })
            return {
                "status": "blocked",
                "reason": governance.get("reason") or "[BLOCKED] document failed governance screen",
            }

        canvas = result.get("canvas", {})
        self.publish_status("FlowCompleted", {
            "squad_id": _SQUAD_ID,
            "correlation_id": payload.get("correlation_id"),
            "result_summary": result.get("status"),
        })
        return {"status": "completed", **canvas}

    # ------------------------------------------------------------------
    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for execute_flow — matches the Router → Orchestrator.run(event) convention."""
        return self.execute_flow(event)
