# SPDX-License-Identifier: Apache-2.0
# k9x_studio — K9EventRouter (SBB)
#
# Single entry point for all backend events. Resolves event_type →
# orchestrator deterministically (register_orchestrator, inherited from
# BaseRouter) and calls it in-process — no Kafka in Phase 2 (DESIGN.md:
# "no Kafka in Phase 1/2"; FastAPI stays synchronous HTTP).
#
# No business logic lives here — purely deterministic dispatch, exactly
# like EOCRouter's routing table, minus the Kafka publish step.

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.router.base_router import BaseRouter


class K9EventRouter(BaseRouter):

    layer = "k9x_studio K9EventRouter SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config or {}, **kwargs)

    # ------------------------------------------------------------------
    def route(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Resolve ``event_type`` to its registered orchestrator and run it.

        Args:
            event_type: deterministic event key, e.g. "spec_import"
            payload:    full event payload (file content, llm_config, ...)

        Raises:
            KeyError: if no orchestrator is registered for event_type
        """
        key = (event_type or "").lower().strip()
        orchestrator = self.registry.get(key)
        if orchestrator is None:
            known = ", ".join(sorted(self.registry.keys())) or "none"
            raise KeyError(f"[{self.layer}] No orchestrator registered for event_type={event_type!r}. Known: {known}")

        event = {**(payload or {}), "event_type": key}
        self.logger.info("[%s] Routing event_type=%s → %s", self.layer, key, orchestrator.__class__.__name__)
        return orchestrator.run(event)

    # ------------------------------------------------------------------
    def supported_event_types(self) -> list:
        return list(self.registry.keys())
