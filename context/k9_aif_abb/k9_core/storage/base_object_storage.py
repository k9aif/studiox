# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
BaseObjectStorage — ABB abstract contract for object/blob storage.

Inheritance hierarchy::

    BaseObjectStorage                   (contract — ABB, this file)
      └── LocalObjectStorageAdapter     (default: local filesystem, zero-dep)
      └── S3ObjectStorageAdapter        (S3 / MinIO, lazy boto3)
      └── IbmCosObjectStorageAdapter    (IBM COS, lazy ibm_boto3)
      └── MyObjectStore                 (SBB — extend for custom provider)

Overrideable surface
--------------------
``upload(bucket, key, data, metadata)``  — **abstract** — store binary data.
``download(bucket, key)``                — **abstract** — retrieve binary data.
``delete(bucket, key)``                  — **abstract** — remove object.
``list_objects(bucket, prefix)``         — **abstract** — list keys in bucket.
``get_uri(bucket, key)``                 — **abstract** — return a URI string for the stored object.
``exists(bucket, key)``                  — optional; default calls ``download()`` and catches.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseObjectStorage(ABC):
    """
    ABB contract for object/blob storage across any backend.

    The Router stores inbound documents here before publishing the event
    to a Kafka topic.  Downstream agents receive only the URI and use
    the same factory-provisioned adapter to retrieve the content.
    """

    # ── Abstract — implement in every adapter ─────────────────────────────

    @abstractmethod
    def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store binary *data* under *bucket*/*key*.

        Args:
            bucket:   logical container name
            key:      object key (path within the bucket)
            data:     raw bytes to store
            metadata: optional key-value pairs stored alongside the object

        Returns:
            URI string referencing the stored object.
        """
        raise NotImplementedError

    @abstractmethod
    def download(self, bucket: str, key: str) -> bytes:
        """Retrieve binary data for *bucket*/*key*.  Raises ``FileNotFoundError`` on miss."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, bucket: str, key: str) -> None:
        """Remove the object at *bucket*/*key*; no-op if absent."""
        raise NotImplementedError

    @abstractmethod
    def list_objects(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """List object keys in *bucket*, optionally filtered by *prefix*."""
        raise NotImplementedError

    @abstractmethod
    def get_uri(self, bucket: str, key: str) -> str:
        """Return a URI string for the stored object (e.g. ``s3://bucket/key``, ``file:///path``)."""
        raise NotImplementedError

    # ── Optional override ─────────────────────────────────────────────────

    def exists(self, bucket: str, key: str) -> bool:
        """Return True if *bucket*/*key* exists in the store."""
        try:
            self.download(bucket, key)
            return True
        except (FileNotFoundError, KeyError, Exception):
            return False
