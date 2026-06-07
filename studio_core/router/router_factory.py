# SPDX-License-Identifier: Apache-2.0
# k9x_studio — router bootstrap (Phase 2)
#
# Builds a single cached K9EventRouter and registers each Phase-2
# orchestrator against its event_type. backend/api/routes.py calls
# get_router() and never touches an orchestrator directly — that keeps
# the HTTP layer thin: receive request → emit event → router.route() →
# return result (see DESIGN.md "Key Design Decisions").
#
# Add a new vertical by: building its Orchestrator + Squad, then adding
# one line to _ROUTES below. No router code changes needed.

from functools import lru_cache
from typing import Any, Dict, Optional

from backend.services.config_service import get_llm_config

from studio_core.router.k9_event_router import K9EventRouter
from orchestrators.spec_import_orchestrator import SpecImportOrchestrator

# event_type → Orchestrator class. Extend here as Phase 2 grows
# (bpmn_import → BPMNImportOrchestrator, generate → ScaffoldOrchestrator, ...).
_ROUTES = {
    "spec_import": SpecImportOrchestrator,
}


@lru_cache(maxsize=1)
def get_router() -> K9EventRouter:
    config: Dict[str, Any] = {"llm": get_llm_config()}
    router = K9EventRouter(config=config)
    for event_type, orchestrator_cls in _ROUTES.items():
        router.register_orchestrator(event_type, orchestrator_cls(config=config))
    return router


def route_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience wrapper used by thin route handlers."""
    return get_router().route(event_type, payload)
