# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
S3ObjectStorageAdapter — OOB S3-compatible object storage (AWS S3 / MinIO).

Requires the ``boto3`` package::

    pip install boto3

YAML config::

    object_storage:
      provider: s3
      endpoint_url: "${S3_ENDPOINT_URL:-http://localhost:9000}"   # MinIO local
      region: "${S3_REGION:-us-east-1}"

Credentials follow the standard boto3 chain:
``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` from environment — never config.yaml.

For local MinIO: set ``S3_ENDPOINT_URL=http://localhost:9000`` and the MinIO
access/secret keys as ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.storage.base_object_storage import BaseObjectStorage

log = logging.getLogger(__name__)


class S3ObjectStorageAdapter(BaseObjectStorage):
    """S3-compatible object storage — works with AWS S3 and MinIO."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        cfg = self._config.get("object_storage", {})
        self._endpoint_url = (
            cfg.get("endpoint_url")
            or os.environ.get("S3_ENDPOINT_URL")
        )
        self._region = cfg.get("region") or os.environ.get("S3_REGION", "us-east-1")
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import boto3  # type: ignore

            kwargs: Dict[str, Any] = {"region_name": self._region}
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            self._client = boto3.client("s3", **kwargs)
            log.info(
                "[S3ObjectStorage] connected endpoint=%s region=%s",
                self._endpoint_url or "AWS default",
                self._region,
            )
        except ImportError as exc:
            raise RuntimeError(
                "boto3 package required for S3ObjectStorageAdapter: pip install boto3"
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
        log.info("[S3ObjectStorage] uploaded %s (%d bytes)", uri, len(data))
        return uri

    def download(self, bucket: str, key: str) -> bytes:
        self._ensure_client()
        try:
            resp = self._client.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read()
        except self._client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"s3://{bucket}/{key} not found")
        except Exception as exc:
            if "NoSuchKey" in str(exc) or "404" in str(exc):
                raise FileNotFoundError(f"s3://{bucket}/{key} not found") from exc
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
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(**kwargs):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def get_uri(self, bucket: str, key: str) -> str:
        return f"s3://{bucket}/{key}"
