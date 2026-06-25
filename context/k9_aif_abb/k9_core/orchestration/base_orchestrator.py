# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# K9-AIF - Base Orchestrator
# Abstract orchestrator foundation for coordinating multiple agents.

import inspect
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.governance.pipeline import NoopGovernance, require_governance

# Optional Zero Trust runtime enforcement layer
try:
    from k9_aif_abb.k9_security.zero_trust.context import (
        ExecutionContext,
        IdentityContext,
        AttributeContext,
        DestinationContext,
    )
    from k9_aif_abb.k9_security.zero_trust.guards import (
        BaseZeroTrustGuard,
        DefaultZeroTrustGuard,
    )
    from k9_aif_abb.k9_security.zero_trust.enforcers import (
        BasePolicyEnforcer,
        RuntimePolicyEnforcer,
    )

    ZERO_TRUST_AVAILABLE = True
except ImportError:
    ZERO_TRUST_AVAILABLE = False
    ExecutionContext = None
    IdentityContext = None
    AttributeContext = None
    DestinationContext = None
    BaseZeroTrustGuard = None
    DefaultZeroTrustGuard = None
    BasePolicyEnforcer = None
    RuntimePolicyEnforcer = None


class BaseOrchestrator(ABC):
    """
    BaseOrchestrator
    =================
    Abstract base class for all orchestrators in the K9-AIF framework.

    Cardinality: Router 1→N Orchestrators, Orchestrator 1→N Squads, Squad 1→N Agents.
    Use ``execute_squads()`` for multi-squad execution with optional parallelism.

    Supports:
    - 1 or more squads (sequential or parallel via execute_squads)
    - monitoring
    - message bus publishing
    - governance pre/post processing
    - optional Zero Trust execution enforcement
    """

    layer: str = "Orchestrator Base"

    # ------------------------------------------------------------------
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        monitor=None,
        message_bus=None,
        governance=None,
        zero_trust_guard=None,
        policy_enforcer=None,
        enable_zero_trust: Optional[bool] = None,
        session_manager=None,
    ):
        self.config = config or {}
        self.monitor = monitor
        self.message_bus = message_bus
        self.governance = require_governance(governance, self.config.get("k9_env"))
        self._session_manager = session_manager or self._bootstrap_session(self.config)

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

    # ------------------------------------------------------------------
    @abstractmethod
    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement execute_flow()")

    # ------------------------------------------------------------------
    def execute_squads(
        self,
        squads,
        payload: Dict[str, Any],
        parallel: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Execute one or more squads owned by this orchestrator.

        An Orchestrator owns 1 or more Squads, each with its own team of
        Agents. When ``parallel=True``, squads execute concurrently via a
        thread pool; results are namespaced by squad_id to prevent collision.

        Returns ``{squad_id: squad_result, ...}`` — one entry per squad.

        Sequential (default) is appropriate when squads feed into each other.
        Parallel is appropriate for cross-cutting or independent squads.
        """
        if not squads:
            return {}

        if not parallel or len(squads) <= 1:
            results = {}
            for squad in squads:
                self.logger.info(
                    "[%s] Executing squad: %s (sequential)", self.layer, squad.squad_id,
                )
                result = squad.execute(payload)
                results[squad.squad_id] = result
            return results

        from concurrent.futures import ThreadPoolExecutor, as_completed

        self.logger.info(
            "[%s] Executing %d squads in parallel: %s",
            self.layer, len(squads), [s.squad_id for s in squads],
        )
        results = {}
        with ThreadPoolExecutor(max_workers=len(squads)) as executor:
            futures = {
                executor.submit(squad.execute, {**payload}): squad
                for squad in squads
            }
            for future in as_completed(futures):
                squad = futures[future]
                try:
                    results[squad.squad_id] = future.result()
                except Exception as exc:
                    self.logger.error(
                        "[%s] Squad %s failed: %s", self.layer, squad.squad_id, exc,
                    )
                    results[squad.squad_id] = {
                        "status": "failed",
                        "squad_id": squad.squad_id,
                        "error": str(exc),
                    }
        return results

    # ------------------------------------------------------------------
    def publish_status(self, status: str, context: Dict[str, Any]):
        event = {"status": status, **context}
        if self.message_bus:
            self.message_bus.publish(event)
        if self.monitor:
            self.monitor.record_event(event)
        self.logger.info(f"[{self.layer}] Status event: {event}")

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
    def apply_zero_trust(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Applies the K9 Zero Trust Execution Layer.

        This is intentionally separate from governance:
        - governance defines policy intent
        - zero trust enforces execution-time control
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
            "[ZeroTrust] decision=%s allowed=%s risk=%s reason=%s",
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

    # ------------------------------------------------------------------
    def _zero_trust_context(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None,
    ):
        ctx = ctx or {}

        return ExecutionContext(
            request_id=payload.get("request_id") or ctx.get("request_id") or "unknown",
            session_id=payload.get("session_id") or ctx.get("session_id"),
            workflow_id=payload.get("workflow_id") or ctx.get("workflow_id"),
            source_type=payload.get("source_type", "orchestrator"),
            action_type=payload.get("action_type", "execute_flow"),
            identity=IdentityContext(
                principal_id=payload.get("principal_id", self.__class__.__name__),
                principal_type=payload.get("principal_type", "orchestrator"),
                roles=payload.get("roles", []),
                tenant_id=payload.get("tenant_id"),
            ),
            attributes=AttributeContext(
                data_sensitivity=payload.get("data_sensitivity", "low"),
                environment=payload.get("environment", self.config.get("environment", "dev")),
                trust_zone=payload.get("trust_zone", "internal"),
                labels=payload.get("labels", {}),
            ),
            destination=DestinationContext(
                destination_type=payload.get("destination_type", "internal_component"),
                destination_name=payload.get("destination_name", self.__class__.__name__),
                destination_uri=payload.get("destination_uri"),
                is_external=payload.get("is_external", False),
            ),
            payload=payload,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _bootstrap_session(config: Dict[str, Any]):
        """Auto-create session manager from config when session.enabled: true. Returns None otherwise."""
        try:
            from k9_aif_abb.k9_factories.session_factory import SessionFactory
            return SessionFactory.create_manager(config)
        except Exception:
            return None

    def _governance_context(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "component": self.__class__.__name__,
            "component_type": "orchestrator",
        }

    def _update_session(self, session_id: str, context_delta: Dict[str, Any]) -> None:
        """
        Persist squad result context back to session after execution.

        Call this at the end of the SBB orchestrator's run() method.
        No-op when no session_manager is configured — existing behaviour preserved.
        """
        if self._session_manager is not None and session_id:
            self._session_manager.on_session_update(session_id, context_delta)