# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/formatters/web_formatter_agent.py

from typing import Any, Dict
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class WebFormatterAgent(BaseAgent):
    """
    K9-AIF WebFormatterAgent
    ------------------------
    SBB that formats structured results into a web-friendly representation.
    Used in demos such as Sports Car Experience Center or WeatherAssist.
    """

    layer = "Formatter SBB"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config=config or {}, name="WebFormatterAgent")

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Format results into an HTML or JSON-friendly view.
        Currently stubbed for smoke testing.
        """
        payload = kwargs.get("payload") or (args[0] if args else {})
        self.log(f"[{self.layer}] Executing formatting for payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'N/A'}")

        # --- Stubbed example HTML rendering ---
        html_output = f"<html><body><pre>{payload}</pre></body></html>"

        result = {
            "formatted": html_output,
            "format": "html",
            "status": "ok",
        }

        self.log(f"[{self.layer}] Produced formatted output", "INFO")
        return result