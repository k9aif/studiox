# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/security_factory.py

"""
SecurityFactory — provisions encryption, IAM, and secret management modules.

Secret manager adapters
-----------------------
``SecretManagerFactory`` is embedded here (same file) to avoid a separate
factory for a closely related concern.  Both follow the PersistenceFactory
static pattern: pre-populated registry, ``register()``, ``get()``, ``create(config)``.

Config key::

    secrets:
      provider: env          # env | vault | aws | ibm  (default: env)

Adapter credentials NEVER go in config.yaml — they come from env variables.

Usage::

    from k9_aif_abb.k9_factories.security_factory import SecretManagerFactory

    sm = SecretManagerFactory.create(config)    # env adapter by default
    api_key = sm.get("MY_API_KEY")              # raises KeyError if absent
"""

from threading import Lock
from typing import Any, Dict, Type
import logging

log = logging.getLogger(__name__)


class SecurityFactory:
    """Static Factory — provisions encryption, IAM, and access control modules."""

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("SecurityFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("SecurityFactory is static and cannot be instantiated")

    @staticmethod
    def register(name: str, sec_cls: Type[Any]) -> None:
        with SecurityFactory._lock:
            SecurityFactory._registry[name] = sec_cls
            SecurityFactory.logger.debug("Registered security backend '%s'", name)

    @staticmethod
    def get(name: str, **kwargs: Any):
        try:
            cls = SecurityFactory._registry[name]
            return cls(**kwargs)
        except KeyError:
            raise ValueError(f"Unknown security backend: {name}")

    @staticmethod
    def bootstrap() -> None:
        if SecurityFactory._bootstrapped:
            return
        SecurityFactory._bootstrapped = True
        SecurityFactory.logger.info("[Factory] Bootstrapped SecurityFactory")


# ── Secret Manager Factory ────────────────────────────────────────────────────

class SecretManagerFactory:
    """
    Static Factory — provisions secret manager adapters.

    Pre-registered adapters: env (default), vault, aws, ibm.
    Custom adapters can be added via ``register()``.
    """

    _registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False
    logger = logging.getLogger("SecretManagerFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("SecretManagerFactory is static and cannot be instantiated")

    @staticmethod
    def _ensure_defaults() -> None:
        if SecretManagerFactory._bootstrapped:
            return
        with SecretManagerFactory._lock:
            if SecretManagerFactory._bootstrapped:
                return
            from k9_aif_abb.k9_security.adapters.env_adapter   import EnvSecretAdapter
            from k9_aif_abb.k9_security.adapters.vault_adapter  import VaultSecretAdapter
            from k9_aif_abb.k9_security.adapters.aws_adapter    import AwsSecretAdapter
            from k9_aif_abb.k9_security.adapters.ibm_adapter    import IbmSecretAdapter

            SecretManagerFactory._registry.update({
                "env":   EnvSecretAdapter,
                "vault": VaultSecretAdapter,
                "aws":   AwsSecretAdapter,
                "ibm":   IbmSecretAdapter,
            })
            SecretManagerFactory._bootstrapped = True
            SecretManagerFactory.logger.info("[Factory] Bootstrapped SecretManagerFactory")

    @staticmethod
    def register(name: str, cls: Type[Any]) -> None:
        """Register a custom secret manager adapter."""
        SecretManagerFactory._ensure_defaults()
        with SecretManagerFactory._lock:
            SecretManagerFactory._registry[name.lower()] = cls
            SecretManagerFactory.logger.debug("Registered secret manager '%s'", name)

    @staticmethod
    def get(name: str, config: Dict[str, Any] = None):
        """Return an instance of the named secret manager adapter."""
        SecretManagerFactory._ensure_defaults()
        cls = SecretManagerFactory._registry.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown secret manager provider: {name}")
        return cls(config=config or {})

    @staticmethod
    def create(config: Dict[str, Any] = None):
        """
        Create a secret manager from config.

        Reads ``config["secrets"]["provider"]`` (default: ``"env"``).
        """
        SecretManagerFactory._ensure_defaults()
        cfg = (config or {})
        provider = cfg.get("secrets", {}).get("provider", "env").lower()
        SecretManagerFactory.logger.info("[Factory] Creating secret manager: %s", provider)
        return SecretManagerFactory.get(provider, config=cfg)
