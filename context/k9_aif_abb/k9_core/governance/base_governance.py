# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# k9_core/governance/base_governance.py

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional

from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseGovernance(BaseComponent, ABC):
    """
    K9-AIF Governance ABB - BaseGovernance
    --------------------------------------
    Abstract base for all governance and compliance policy blocks in K9-AIF.

    Responsibilities:
    - Define standard pre- and post-processing hooks for payload governance.
    - Provide unified, layer-aware logging (visible in the live console).
    - Integrate with the Monitoring ABB for real-time observability.
    """

    layer = "Governance ABB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None):
        super().__init__(monitor=monitor)
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def log(self, message: str, level: str = "INFO"):
        """
        Override BaseComponent.log() to also write to the Python logger.
        This ensures unified console + framework logging.
        """
        await super().log(message, level)
        if hasattr(self.logger, level.lower()):
            getattr(self.logger, level.lower())(f"[{self.layer}] {message}")
        else:
            self.logger.info(f"[{self.layer}] {message}")

    @abstractmethod
    async def pre_process(self, payload: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute governance and compliance checks BEFORE sending payload outward.
        Must be implemented by subclasses (e.g., Guardian, SecurityPolicy).
        """
        raise NotImplementedError

    @abstractmethod
    async def post_process(self, payload: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute governance and compliance checks AFTER payload is received or processed.
        Must be implemented by subclasses.
        """
        raise NotImplementedError