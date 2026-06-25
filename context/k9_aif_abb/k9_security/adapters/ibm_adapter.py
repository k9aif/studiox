# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
IbmSecretAdapter — IBM Secrets Manager adapter.

Requires the ``ibm-platform-services`` package::

    pip install ibm-platform-services ibm-cloud-sdk-core

YAML config::

    secrets:
      provider: ibm
      ibm_sm_endpoint: https://<instance>.secrets-manager.appdomain.cloud
      ibm_sm_secret_group: default      # optional secret group name

IBM API key comes from environment only::

    IBM_CLOUD_API_KEY   <your_api_key>

SBB extension::

    class AppIbmAdapter(IbmSecretAdapter):
        def _resolve_name(self, key):
            return f"myapp-{key}"
"""

import logging
import os
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.security.base_secret_manager import BaseSecretManager

log = logging.getLogger(__name__)


class IbmSecretAdapter(BaseSecretManager):
    """Retrieves secrets from IBM Secrets Manager."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        cfg = self._config.get("secrets", self._config)
        self._endpoint = cfg.get("ibm_sm_endpoint", "")
        self._group    = cfg.get("ibm_sm_secret_group", "default")
        self._api_key  = os.environ.get("IBM_CLOUD_API_KEY", "")
        self._client   = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from ibm_platform_services import SecretsManagerV2  # type: ignore
            from ibm_cloud_sdk_core.authenticators import IAMAuthenticator  # type: ignore
            if not self._api_key:
                raise RuntimeError("IBM_CLOUD_API_KEY environment variable not set")
            auth = IAMAuthenticator(self._api_key)
            self._client = SecretsManagerV2(authenticator=auth)
            self._client.set_service_url(self._endpoint)
            log.info("[IbmSecretAdapter] client initialised (endpoint=%s)", self._endpoint)
        except ImportError as exc:
            raise RuntimeError(
                "ibm-platform-services and ibm-cloud-sdk-core required: "
                "pip install ibm-platform-services ibm-cloud-sdk-core"
            ) from exc

    def _resolve_name(self, key: str) -> str:
        return key

    def get(self, key: str) -> str:
        self._ensure_client()
        name = self._resolve_name(key)
        try:
            resp = self._client.list_secrets(groups=[self._group]).get_result()
            for secret in resp.get("secrets", []):
                if secret.get("name") == name:
                    secret_id = secret["id"]
                    detail = self._client.get_secret(id=secret_id).get_result()
                    value = (
                        detail.get("payload")
                        or detail.get("secret_data", {}).get("payload", "")
                    )
                    if not value:
                        raise KeyError(key)
                    return str(value)
            raise KeyError(key)
        except KeyError:
            raise
        except Exception as exc:
            log.warning("[IbmSecretAdapter] failed to retrieve %s: %s", key, exc)
            raise KeyError(key) from exc
