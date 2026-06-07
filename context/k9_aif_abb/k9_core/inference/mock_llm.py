# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/mock_llm.py

import logging
from typing import Any, Optional

from k9_aif_abb.k9_core.inference.base_llm import BaseLLM


class MockLLM(BaseLLM):
    """
    K9-AIF Inference SBB - MockLLM
    ------------------------------
    Simple deterministic LLM mock used for demos.
    Avoids async complexity for clean synchronous execution.
    """

    layer = "Inference SBB"

    def __init__(self, monitor: Optional[Any] = None, **kwargs: Any):
        super().__init__(name="MockLLM", monitor=monitor)
        self.kwargs = kwargs
        self.logger = logging.getLogger(self.name)

    # ------------------------------------------------------------------
    # Helper: synchronous safe log
    # ------------------------------------------------------------------
    def _safe_log(self, message: str, level: str = "INFO"):
        """Fallback logger that calls BaseLLM.log() synchronously."""
        try:
            # Call BaseComponent.log() synchronously if available
            super_log = getattr(super(), "log", None)
            if callable(super_log):
                super_log(message, level)
            # Mirror to standard Python logger
            if hasattr(self.logger, level.lower()):
                getattr(self.logger, level.lower())(f"[{self.layer}] {message}")
            else:
                self.logger.info(f"[{self.layer}] {message}")
        except Exception as e:
            self.logger.warning(f"[{self.layer}] Logging error: {e}")

    # ------------------------------------------------------------------
    # Core inference methods
    # ------------------------------------------------------------------
    def generate(self, prompt: str) -> str:
        """Generate a deterministic mock response."""
        self._safe_log(f"MockLLM generating mock response for prompt: {prompt}", level="DEBUG")
        return f"[MOCK RESPONSE for: {prompt}]"

    def __call__(self, prompt: str) -> str:
        """Allow direct function-style invocation."""
        return self.generate(prompt)

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._safe_log("MockLLM initialized (simulation mode)", level="INFO")

    def stop(self) -> None:
        self._safe_log("MockLLM stopped", level="INFO")