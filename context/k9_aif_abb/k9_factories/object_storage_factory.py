# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
ObjectStorageFactory — static factory for object/blob storage backends.

Pre-registered adapters: local (default), s3 (OOB — works with MinIO and AWS S3), ibm.

YAML config::

    object_storage:
      provider: local           # local | s3 | ibm  (default: local)
      # provider-specific keys below — credentials from env vars only

Usage::

    from k9_aif_abb.k9_factories.object_storage_factory import ObjectStorageFactory

    store = ObjectStorageFactory.create(config)
    uri   = store.upload("documents", "claim-001/form.pdf", file_bytes)
    data  = store.download("documents", "claim-001/form.pdf")
"""

from threading import Lock
from typing import Any, Dict, Type
import logging

log = logging.getLogger("ObjectStorageFactory")


class ObjectStorageFactory:
    """Static Factory — provisions object storage backends."""

    _registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs):
        raise RuntimeError("ObjectStorageFactory is static and cannot be instantiated")

    @staticmethod
    def _ensure_defaults() -> None:
        if ObjectStorageFactory._bootstrapped:
            return
        with ObjectStorageFactory._lock:
            if ObjectStorageFactory._bootstrapped:
                return
            from k9_aif_abb.k9_storage.adapters.local_adapter   import LocalObjectStorageAdapter
            from k9_aif_abb.k9_storage.adapters.s3_adapter       import S3ObjectStorageAdapter
            from k9_aif_abb.k9_storage.adapters.ibm_cos_adapter  import IbmCosObjectStorageAdapter

            ObjectStorageFactory._registry.update({
                "local": LocalObjectStorageAdapter,
                "s3":    S3ObjectStorageAdapter,
                "ibm":   IbmCosObjectStorageAdapter,
            })
            ObjectStorageFactory._bootstrapped = True
            log.info("[Factory] Bootstrapped ObjectStorageFactory")

    @staticmethod
    def register(name: str, cls: Type[Any]) -> None:
        """Register a custom object storage adapter."""
        ObjectStorageFactory._ensure_defaults()
        with ObjectStorageFactory._lock:
            ObjectStorageFactory._registry[name.lower()] = cls
            log.debug("[Factory] Registered object storage adapter '%s'", name)

    @staticmethod
    def get(name: str, config: Dict[str, Any] = None):
        """Return an instance of the named object storage adapter."""
        ObjectStorageFactory._ensure_defaults()
        cls = ObjectStorageFactory._registry.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown object storage provider: {name}")
        return cls(config=config or {})

    @staticmethod
    def create(config: Dict[str, Any] = None):
        """
        Create an object storage backend from config.

        Reads ``config["object_storage"]["provider"]`` (default: ``"local"``).
        """
        ObjectStorageFactory._ensure_defaults()
        cfg = config or {}
        provider = cfg.get("object_storage", {}).get("provider", "local").lower()
        log.info("[Factory] Creating object storage: %s", provider)
        return ObjectStorageFactory.get(provider, config=cfg)
