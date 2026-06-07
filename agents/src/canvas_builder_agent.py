# SPDX-License-Identifier: Apache-2.0
# k9x_studio — CanvasBuilderAgent (GREEN — final response assembly)

from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class CanvasBuilderAgent(BaseAgent):

    layer = "k9x_studio CanvasBuilderAgent SBB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None, **kwargs):
        super().__init__(config or {}, monitor=monitor, **kwargs)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        parsed = payload.get("parsed", {})
        scored = payload.get("scored", {})

        response: Dict[str, Any] = {
            "suggestion": scored.get("suggestion", {}),
            "intake": parsed.get("intake", {}),
            "source": scored.get("source", "spec"),
        }
        if scored.get("scoring"):
            response["scoring"] = scored["scoring"]

        self.publish_event({"type": "CanvasSuggestionBuilt", "agent": "CanvasBuilderAgent",
                            "source": response["source"]})
        return response
