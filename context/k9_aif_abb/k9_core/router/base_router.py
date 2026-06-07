# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import inspect
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.governance.pipeline import NoopGovernance, require_governance

try:
    from k9_aif_abb.k9_security.zero_trust.context import (
        ExecutionContext,
        IdentityContext,
        AttributeContext,
        DestinationContext,
    )
    from k9_aif_abb.k9_security.zero_trust.guards import (
        DefaultZeroTrustGuard,
    )
    from k9_aif_abb.k9_security.zero_trust.enforcers import (
        RuntimePolicyEnforcer,
    )

    ZERO_TRUST_AVAILABLE = True
except ImportError:
    ZERO_TRUST_AVAILABLE = False


class BaseRouter(ABC):
    """
    BaseRouter
    ==========
    Abstract foundation for routing logic in the K9-AIF framework.

    Supports:
    - intent-based routing
    - governance pre/post hooks
    - optional Zero Trust execution enforcement
    """

    layer: str = "Router Base"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        monitor=None,
        message_bus=None,
        governance=None,
        zero_trust_guard=None,
        policy_enforcer=None,
        enable_zero_trust: Optional[bool] = None,
    ):
        self.config = config or {}
        self.monitor = monitor
        self.message_bus = message_bus
        self.governance = require_governance(governance, self.config.get("k9_env"))
        self.registry: Dict[str, Any] = {}

        self.enable_zero_trust = (
            enable_zero_trust
            if enable_zero_trust is not None
            else self.config.get("enable_zero_trust", False)
        )

        if self.enable_zero_trust and ZERO_TRUST_AVAILABLE:
            self.zero_trust_guard = zero_trust_guard or DefaultZeroTrustGuard()
            self.policy_enforcer = policy_enforcer or RuntimePolicyEnforcer()
        else:
            self.zero_trust_guard = None
            self.policy_enforcer = None

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"[{self.layer}] Initialized with config: {self.config}")

    def register_orchestrator(self, intent: str, orchestrator: Any):
        self.registry[intent] = orchestrator
        self.logger.info(f"[{self.layer}] Registered orchestrator for intent: {intent}")

    @abstractmethod
    def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement route()")

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return payload

    def apply_zero_trust(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Applies the K9 Zero Trust Execution Layer before routing.
        """

        if not self.enable_zero_trust:
            return {
                "allowed": True,
                "decision": "BYPASSED",
                "reason": "Zero Trust disabled",
                "risk_score": 0.0,
                "obligations": [],
                "payload": payload,
            }

        if not ZERO_TRUST_AVAILABLE:
            self.logger.warning(
                "[ZeroTrust] Enabled but zero trust package is unavailable. Bypassing."
            )
            return {
                "allowed": True,
                "decision": "UNAVAILABLE_BYPASS",
                "reason": "Zero Trust package unavailable",
                "risk_score": 0.0,
                "obligations": [],
                "payload": payload,
            }

        execution_context = self._zero_trust_context(payload, ctx)

        decision = self.zero_trust_guard.evaluate(execution_context)
        decision = self.policy_enforcer.enforce(execution_context, decision)

        self.logger.info(
            "[ZeroTrust][Router] decision=%s allowed=%s risk=%s reason=%s",
            decision.decision.value,
            decision.allowed,
            decision.risk_score,
            decision.reason,
        )

        return {
            "allowed": decision.allowed,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
            "obligations": decision.obligations,
            "payload": execution_context.payload,
        }

    def _zero_trust_context(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ):
        ctx = ctx or {}

        return ExecutionContext(
            request_id=payload.get("request_id")
            or ctx.get("request_id")
            or str(uuid.uuid4()),
            session_id=payload.get("session_id") or ctx.get("session_id"),
            workflow_id=payload.get("workflow_id") or ctx.get("workflow_id"),
            source_type=payload.get("source_type", "router"),
            action_type=payload.get("action_type", "route"),
            identity=IdentityContext(
                principal_id=payload.get("principal_id", self.__class__.__name__),
                principal_type=payload.get("principal_type", "router"),
                roles=payload.get("roles", []),
                tenant_id=payload.get("tenant_id"),
            ),
            attributes=AttributeContext(
                data_sensitivity=payload.get("data_sensitivity", "low"),
                environment=payload.get(
                    "environment",
                    self.config.get("environment", "dev"),
                ),
                trust_zone=payload.get("trust_zone", "internal"),
                labels=payload.get("labels", {}),
            ),
            destination=DestinationContext(
                destination_type=payload.get("destination_type", "orchestrator"),
                destination_name=payload.get("destination_name", "routing_registry"),
                destination_uri=payload.get("destination_uri"),
                is_external=payload.get("is_external", False),
            ),
            payload=payload,
        )

    async def apply_pre_governance(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = self.governance.pre_process(payload, ctx or self._governance_context())
        if inspect.isawaitable(result):
            result = await result
        return result

    async def apply_post_governance(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = self.governance.post_process(payload, ctx or self._governance_context())
        if inspect.isawaitable(result):
            result = await result
        return result

    def _governance_context(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "component": self.__class__.__name__,
            "component_type": "router",
        }