from .context import ExecutionContext
from .decisions import TrustDecision, TrustDecisionType


class BasePolicyEnforcer:
    def enforce(
        self,
        context: ExecutionContext,
        decision: TrustDecision,
    ) -> TrustDecision:
        raise NotImplementedError


class RuntimePolicyEnforcer(BasePolicyEnforcer):
    def enforce(
        self,
        context: ExecutionContext,
        decision: TrustDecision,
    ) -> TrustDecision:
        if decision.decision == TrustDecisionType.DENY:
            return decision

        if "audit_log" in decision.obligations:
            print(
                f"[ZeroTrust][AUDIT] request_id={context.request_id} "
                f"principal={context.identity.principal_id} "
                f"destination={context.destination.destination_name} "
                f"decision={decision.decision.value} "
                f"risk={decision.risk_score}"
            )

        if "mask_sensitive_data" in decision.obligations:
            context.payload["zero_trust_masked"] = True
            self._mask_dict(context.payload)

        return decision

    def _mask_dict(self, data: dict):
        sensitive_keys = {
            "ssn",
            "customer_ssn",
            "dob",
            "credit_card",
            "account_number",
        }

        for key, value in data.items():
            if isinstance(value, dict):
                self._mask_dict(value)
            elif key.lower() in sensitive_keys:
                data[key] = "***MASKED***"