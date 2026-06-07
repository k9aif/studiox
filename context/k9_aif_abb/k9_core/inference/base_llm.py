# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/base_llm.py

import logging
import asyncio
from typing import Optional
from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseLLM(BaseComponent):
    """
    K9-AIF Inference ABB - BaseLLM
    ------------------------------
    Abstract base class for all Large Language Model interfaces.

    Responsibilities:
    - Define the core `generate()` contract for subclasses.
    - Integrate with BaseComponent for telemetry.
    - Serve as the parent for all concrete LLM SBBs.
    """

    layer = "Inference ABB"

    def __init__(self, name: str = "BaseLLM", monitor: Optional[object] = None):
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """
        Async-safe logging:
        - If parent's log() is sync, call it directly.
        - If parent's log() returns a coroutine, await it.
        - Avoid duplicate logs: only fall back to Python logging if no parent logger exists.
        """
        try:
            parent_log = getattr(super(), "log", None)
            handled_by_parent = False

            if callable(parent_log):
                result = parent_log(message, level)
                if asyncio.iscoroutine(result):
                    await result
                handled_by_parent = True

            if not handled_by_parent:
                # Fallback to standard Python logging
                py_level = getattr(logging, level.upper(), logging.INFO)
                self.logger.log(py_level, message)

        except Exception as e:
            # Last-resort fallback to stdout to avoid crashing on logging
            print(f"[LLM LOG ERROR] {e}: {message}")

    # ------------------------------------------------------------------
    # Abstract inference contract
    # ------------------------------------------------------------------
    def generate(self, prompt: str) -> str:
        """
        Generate a text completion or inference result for a given prompt.
        Subclasses must override this method to connect to their backend LLM.
        """
        raise NotImplementedError("Subclasses must implement generate()")