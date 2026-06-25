# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
AwsSecretAdapter — AWS Secrets Manager adapter.

Requires the ``boto3`` package::

    pip install boto3

YAML config::

    secrets:
      provider: aws
      aws_region: us-east-1              # or set AWS_DEFAULT_REGION env var

AWS credentials follow the standard boto3 credential chain
(env vars → ~/.aws/credentials → IAM role) — never stored in config.yaml.

SBB extension::

    class TaggedAwsAdapter(AwsSecretAdapter):
        def _resolve_name(self, key):
            env = self._config.get("environment", "dev")
            return f"k9aif/{env}/{key}"
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.security.base_secret_manager import BaseSecretManager

log = logging.getLogger(__name__)


class AwsSecretAdapter(BaseSecretManager):
    """Retrieves secrets from AWS Secrets Manager."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        cfg = self._config.get("secrets", self._config)
        self._region = cfg.get("aws_region") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import boto3  # type: ignore
            self._client = boto3.client("secretsmanager", region_name=self._region)
            log.info("[AwsSecretAdapter] client initialised (region=%s)", self._region)
        except ImportError as exc:
            raise RuntimeError(
                "boto3 package required for AwsSecretAdapter: pip install boto3"
            ) from exc

    def _resolve_name(self, key: str) -> str:
        return key

    def get(self, key: str) -> str:
        self._ensure_client()
        name = self._resolve_name(key)
        try:
            resp = self._client.get_secret_value(SecretId=name)
            raw = resp.get("SecretString") or resp.get("SecretBinary", b"").decode()
            # If the secret is a JSON object, try extracting the key directly
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    value = parsed.get(key)
                    if value is not None:
                        return str(value)
                    # Return the whole JSON string if key not found in object
                    return raw
            except (json.JSONDecodeError, TypeError):
                pass
            if not raw:
                raise KeyError(key)
            return raw
        except KeyError:
            raise
        except Exception as exc:
            log.warning("[AwsSecretAdapter] failed to retrieve %s: %s", key, exc)
            raise KeyError(key) from exc
