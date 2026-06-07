# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# K9-AIF - Base Agent
# Core abstract base for all K9-AIF domain and orchestration agents.

import inspect
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from k9_aif_abb.k9_core.governance.pipeline import (
    NoopGovernance,
    require_governance,
)


class BaseAgent(ABC):
    """
    BaseAgent
    =========
    Abstract foundation for all K9-AIF agents.
    """

    layer: str = "Agent Base"

    # ------------------------------------------------------------------
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        monitor=None,
        message_bus=None,
        governance=None,
    ):
        self.config = config or {}
        self.monitor = monitor
        self.message_bus = message_bus
        self.governance = require_governance(
            governance, self.config.get("k9_env")
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"[{self.layer}] Initialized with config: {self.config}")

    # ------------------------------------------------------------------
    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement execute()")

    # ------------------------------------------------------------------
    def publish_event(self, event: Dict[str, Any]):
        if self.message_bus:
            self.message_bus.publish(event)
        if self.monitor:
            self.monitor.record_event(event)
        self.logger.info(f"[{self.layer}] Event published: {event}")

    # ------------------------------------------------------------------
    async def apply_pre_governance(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        result = self.governance.pre_process(
            payload,
            ctx or self._governance_context(),
        )
        if inspect.isawaitable(result):
            result = await result
        return result

    # ------------------------------------------------------------------
    async def apply_post_governance(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        result = self.governance.post_process(
            payload,
            ctx or self._governance_context(),
        )
        if inspect.isawaitable(result):
            result = await result
        return result

    # ------------------------------------------------------------------
    def enforce_governance(self) -> None:
        """
        Assert that a real governance pipeline is wired up.

        Call this at the top of ``execute()`` in any agent that requires
        governed operation.  The check is environment-aware:

        - **development / test** — logs a WARNING and continues; NoopGovernance
          is tolerated so local development is not blocked.
        - **all other environments** — raises :class:`PermissionError` if the
          active governance is :class:`NoopGovernance`, preventing ungoverned
          execution from reaching production workloads.

        Raises:
            PermissionError: if governance is NoopGovernance outside dev/test.
        """
        if not isinstance(self.governance, NoopGovernance):
            return  # real governance is configured — nothing to do

        resolved_env = os.getenv("K9_ENV", "production").lower()
        if resolved_env in ("development", "dev", "test"):
            self.logger.warning(
                "[%s] enforce_governance(): NoopGovernance active in %s environment — "
                "proceeding without enforcement.",
                self.layer,
                resolved_env,
            )
            return

        raise PermissionError(
            f"[{self.layer}] enforce_governance() failed: NoopGovernance is active in "
            f"{resolved_env!r} environment. Provide a real governance pipeline."
        )

    # ------------------------------------------------------------------
    def _governance_context(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "component": self.__class__.__name__,
            "component_type": "agent",
        }