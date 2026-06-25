# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
IbmCosObjectStorageAdapter — IBM Cloud Object Storage adapter.

Requires the ``ibm-cos-sdk`` package::

    pip install ibm-cos-sdk

YAML config::

    object_storage:
      provider: ibm
      endpoint_url: "${IBM_COS_ENDPOINT}"
      region: "${IBM_COS_REGION:-us-south}"

Credentials from environment only — never config.yaml:
``IBM_COS_API_KEY``        — IAM API key
``IBM_COS_INSTANCE_CRN``   — service instance CRN
"""

import logging
import os
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.storage.base_object_storage import BaseObjectStorage

log = logging.getLogger(__name__)


class IbmCosObjectStorageAdapter(BaseObjectStorage):
    """IBM Cloud Object Storage adapter via ibm_boto3."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        cfg = self._config.get("object_storage", {})
        self._endpoint_url = (
            cfg.get("endpoint_url")
            or os.environ.get("IBM_COS_ENDPOINT")
        )
        self._region = cfg.get("region") or os.environ.get("IBM_COS_REGION", "us-south")
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import ibm_boto3  # type: ignore
            from ibm_botocore.client import Config  # type: ignore

            api_key = os.environ.get("IBM_COS_API_KEY", "")
            instance_crn = os.environ.get("IBM_COS_INSTANCE_CRN", "")

            self._client = ibm_boto3.client(
                "s3",
                ibm_api_key_id=api_key,
                ibm_service_instance_id=instance_crn,
                config=Config(signature_version="oauth"),
                endpoint_url=self._endpoint_url,
            )
            log.info(
                "[IbmCosObjectStorage] connected endpoint=%s region=%s",
                self._endpoint_url or "default",
                self._region,
            )
        except ImportError as exc:
            raise RuntimeError(
                "ibm-cos-sdk package required for IbmCosObjectStorageAdapter: "
                "pip install ibm-cos-sdk"
            ) from exc

    def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._ensure_client()
        put_kwargs: Dict[str, Any] = {"Bucket": bucket, "Key": key, "Body": data}
        if metadata:
            put_kwargs["Metadata"] = {str(k): str(v) for k, v in metadata.items()}
        self._client.put_object(**put_kwargs)
        uri = self.get_uri(bucket, key)
        log.info("[IbmCosObjectStorage] uploaded %s (%d bytes)", uri, len(data))
        return uri

    def download(self, bucket: str, key: str) -> bytes:
        self._ensure_client()
        try:
            resp = self._client.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read()
        except Exception as exc:
            if "NoSuchKey" in str(exc) or "404" in str(exc):
                raise FileNotFoundError(f"cos://{bucket}/{key} not found") from exc
            raise

    def delete(self, bucket: str, key: str) -> None:
        self._ensure_client()
        self._client.delete_object(Bucket=bucket, Key=key)

    def list_objects(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        self._ensure_client()
        kwargs: Dict[str, Any] = {"Bucket": bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        keys: List[str] = []
        resp = self._client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            keys.append(obj["Key"])
        while resp.get("IsTruncated"):
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
            resp = self._client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def get_uri(self, bucket: str, key: str) -> str:
        return f"cos://{bucket}/{key}"
