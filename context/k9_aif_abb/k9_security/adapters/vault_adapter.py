# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
VaultSecretAdapter — HashiCorp Vault secret manager adapter.

Reads secrets from a Vault KV v2 mount.  Requires the ``hvac`` package::

    pip install hvac

YAML config::

    secrets:
      provider: vault
      vault_addr: ${VAULT_ADDR}           # read from env at startup
      vault_token: ${VAULT_TOKEN}         # read from env at startup
      vault_mount: secret                 # KV v2 mount path (default: secret)
      vault_path_prefix: k9aif/           # prepended to every key (default: "")

Environment variables (never stored in config.yaml)::

    VAULT_ADDR    https://vault.example.com
    VAULT_TOKEN   s.xxxxxxxxxxxx

SBB extension::

    class AppVaultAdapter(VaultSecretAdapter):
        def _resolve_path(self, key):
            return f"myapp/services/{key}"
"""

import logging
import os
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.security.base_secret_manager import BaseSecretManager

log = logging.getLogger(__name__)


class VaultSecretAdapter(BaseSecretManager):
    """Retrieves secrets from HashiCorp Vault KV v2."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        cfg = self._config.get("secrets", self._config)

        # Credentials come from env, never from config.yaml
        self._addr   = os.environ.get("VAULT_ADDR",  cfg.get("vault_addr", ""))
        self._token  = os.environ.get("VAULT_TOKEN", cfg.get("vault_token", ""))
        self._mount  = cfg.get("vault_mount", "secret")
        self._prefix = cfg.get("vault_path_prefix", "")
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import hvac  # type: ignore
            self._client = hvac.Client(url=self._addr, token=self._token)
            if not self._client.is_authenticated():
                raise RuntimeError("Vault authentication failed — check VAULT_TOKEN")
            log.info("[VaultSecretAdapter] authenticated at %s", self._addr)
        except ImportError as exc:
            raise RuntimeError(
                "hvac package required for VaultSecretAdapter: pip install hvac"
            ) from exc

    def _resolve_path(self, key: str) -> str:
        return f"{self._prefix}{key}" if self._prefix else key

    def get(self, key: str) -> str:
        self._ensure_client()
        path = self._resolve_path(key)
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self._mount, path=path
            )
            value = resp["data"]["data"].get(key)
            if value is None:
                raise KeyError(key)
            return str(value)
        except Exception as exc:
            # Normalise all Vault errors to KeyError so callers handle uniformly
            if isinstance(exc, KeyError):
                raise
            log.warning("[VaultSecretAdapter] failed to retrieve %s: %s", key, exc)
            raise KeyError(key) from exc
