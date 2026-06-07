# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/presentation/base_ui.py

from abc import ABC, abstractmethod
import json
import logging
from typing import Dict, Any, Optional

from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseUI(BaseComponent, ABC):
    """
    K9-AIF Presentation ABB - BaseUI
    --------------------------------
    Abstract base class for all User Interface components in K9-AIF.
    Defines the contract for rendering responses back to the end-user
    or to an upstream presentation layer (web, console, API, etc.).

    Responsibilities:
    - Standardize render() across all UI adapters.
    - Provide layer-aware telemetry visible in Monitoring ABB.
    - Allow UIs to be instrumented within end-to-end orchestrations.
    """

    layer = "Presentation ABB"

    def __init__(self, name: str = "BaseUI", monitor: Optional[Any] = None):
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(message, level)
        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

    @abstractmethod
    def render(self, response: Dict[str, Any]) -> None:
        """Render the response to the end-user or UI."""
        raise NotImplementedError


class ConsoleUI(BaseUI):
    """
    K9-AIF Presentation SBB - ConsoleUI
    -----------------------------------
    Default implementation that prints responses to the console.
    Useful for local demos, tests, and headless orchestrations.
    """

    def __init__(self, monitor: Optional[Any] = None):
        super().__init__(name="ConsoleUI", monitor=monitor)

    def render(self, response: Dict[str, Any]) -> None:
        self.logger.info(f"[{self.layer}:{self.name}] Rendering response to console")
        print(json.dumps(response, indent=2))