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
from pathlib import Path
from typing import Any, Dict, Optional

from k9_aif_abb.k9_squad.squad_loader import SquadLoader

from backend.services.config_service import get_llm_config

from studio_core.router.k9_event_router import K9EventRouter
from orchestrators.spec_import_orchestrator import SpecImportOrchestrator

_AGENTS_DIR = Path(__file__).resolve().parents[2] / "agents" / "yaml"

# event_type → Orchestrator class. Extend here as Phase 2 grows
# (bpmn_import → BPMNImportOrchestrator, generate → ScaffoldOrchestrator, ...).
_ROUTES = {
    "spec_import": SpecImportOrchestrator,
}


# Studio's own agents are K9-AIF agents, so governance by construction applies to them: with nothing
# configured they refuse to run in production (K9_ENV unset), which broke spec import for pip users.
# An uploaded spec is untrusted input, so screen it for prompt injection on the way in. Size is left
# to the upload limit (specs are larger than InputSizeCheck's chat-sized default).
_STUDIO_SHIELD: Dict[str, Any] = {
    "shield": {
        "enabled": True,
        "ingress": {"checks": ["PromptInjectionCheck"]},
        "egress": {"checks": []},
    }
}


@lru_cache(maxsize=1)
def get_router() -> K9EventRouter:
    config: Dict[str, Any] = {"llm": get_llm_config(), "security": _STUDIO_SHIELD}
    router = K9EventRouter(config=config)
    # The squad layer, built once: orchestrators load squads by YAML file and id
    # through it; it builds the agents each squad's YAML names (class + module).
    squads = SquadLoader.from_agents(_AGENTS_DIR, config=config)
    for event_type, orchestrator_cls in _ROUTES.items():
        router.register_orchestrator(event_type, orchestrator_cls(config=config, squads=squads))
    return router


def route_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience wrapper used by thin route handlers."""
    return get_router().route(event_type, payload)
