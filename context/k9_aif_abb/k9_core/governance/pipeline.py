# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


class GovernanceConfigError(RuntimeError):
    """Raised when governance is required but not configured."""


class NoopGovernance:
    """
    Passthrough governance — valid only in development/test environments.

    Do NOT use in production. Pass an explicit governance instance or set
    K9_ENV=development to permit this fallback.
    """

    def pre_process(self, payload: dict, ctx: dict | None = None) -> dict:
        return payload

    def post_process(self, payload: dict, ctx: dict | None = None) -> dict:
        return payload


def require_governance(governance: Any, env: str | None = None) -> Any:
    """
    Resolve the governance object for a component at initialisation time.

    Rules:
    - If *governance* is provided → use it as-is.
    - If *governance* is None and the environment is ``development`` or
      ``test`` → log a WARNING and fall back to :class:`NoopGovernance`.
    - If *governance* is None in any other environment → log an ERROR
      (misconfiguration is clearly visible) and still return
      :class:`NoopGovernance` so the process can start.  Components that
      *require* governed execution must call
      :py:meth:`BaseAgent.enforce_governance` inside ``execute()``; that
      is where the hard fail occurs.

    The resolved environment is taken from the *env* argument first, then
    the ``K9_ENV`` environment variable, defaulting to ``"production"``.
    """
    if governance is not None:
        return governance

    resolved_env = (env or os.getenv("K9_ENV", "production")).lower()

    if resolved_env in ("development", "dev", "test"):
        log.warning(
            "[Governance] No governance pipeline provided — using NoopGovernance "
            "(K9_ENV=%s). This is NOT safe for production.",
            resolved_env,
        )
    else:
        log.error(
            "[Governance] No governance pipeline configured (K9_ENV=%s). "
            "NoopGovernance is active — governed agents will refuse to execute. "
            "Pass an explicit governance instance or set K9_ENV=development.",
            resolved_env,
        )

    return NoopGovernance()