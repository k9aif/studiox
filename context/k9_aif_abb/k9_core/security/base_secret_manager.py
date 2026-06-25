# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
BaseSecretManager — ABB abstract contract for secret management.

Inheritance hierarchy::

    BaseSecretManager               (contract — ABB, this file)
      └── EnvSecretAdapter          (default: reads os.environ)
      └── VaultSecretAdapter        (HashiCorp Vault)
      └── AwsSecretAdapter          (AWS Secrets Manager)
      └── IbmSecretAdapter          (IBM Secrets Manager)
      └── MySecretAdapter           (SBB — extend for domain/infra-specific store)

Overrideable surface
--------------------
``get(key)``      — **abstract** — return secret string or raise ``KeyError``.
``get_many(keys)``— optional; default calls ``get()`` for each key.
``exists(key)``   — optional; default calls ``get()`` and catches ``KeyError``.

Design constraints
------------------
- Secrets NEVER appear in config.yaml — provider selection via config is safe;
  credentials for the provider itself belong in environment variables.
- ``get()`` raises ``KeyError`` when a secret is absent; callers must handle it.
- ``get_many()`` returns a partial dict — missing keys are omitted, not None.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseSecretManager(ABC):
    """
    ABB contract for secret retrieval across any secrets backend.

    Minimal SBB implementation::

        class MySecretManager(BaseSecretManager):
            def get(self, key: str) -> str:
                return my_backend.fetch(key)
    """

    # ── Abstract — implement in every adapter ─────────────────────────────────

    @abstractmethod
    def get(self, key: str) -> str:
        """
        Return the secret value for *key*.

        Raises:
            KeyError: when the secret does not exist or cannot be retrieved.
        """
        raise NotImplementedError

    # ── Optional overrides ────────────────────────────────────────────────────

    def get_many(self, keys: List[str]) -> Dict[str, str]:
        """
        Return a dict of ``{key: value}`` for all secrets that exist.

        Missing keys are silently omitted; callers should check for presence.
        Override for backends that support batch retrieval natively.
        """
        result: Dict[str, str] = {}
        for k in keys:
            try:
                result[k] = self.get(k)
            except KeyError:
                pass
        return result

    def exists(self, key: str) -> bool:
        """Return True if the secret exists and is retrievable."""
        try:
            self.get(key)
            return True
        except KeyError:
            return False
