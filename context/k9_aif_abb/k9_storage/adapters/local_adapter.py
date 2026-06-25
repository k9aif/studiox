# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
LocalObjectStorageAdapter — default filesystem-backed object storage.

Zero dependencies.  Suitable for local development, unit tests, and
single-node deployments.  Objects are written to ``<root>/<bucket>/<key>``.

YAML config::

    object_storage:
      provider: local                    # default when block is absent
      root: ./object_store              # base directory (default: ./object_store)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.storage.base_object_storage import BaseObjectStorage

log = logging.getLogger(__name__)


class LocalObjectStorageAdapter(BaseObjectStorage):
    """Filesystem-backed object storage — zero-config default."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        cfg = self._config.get("object_storage", {})
        self._root = Path(cfg.get("root", "object_store"))
        self._root.mkdir(parents=True, exist_ok=True)
        log.info("[LocalObjectStorage] root=%s", self._root)

    def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        bucket_dir = self._root / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        obj_path = bucket_dir / key
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(data)
        uri = self.get_uri(bucket, key)
        log.info("[LocalObjectStorage] uploaded %s (%d bytes)", uri, len(data))
        return uri

    def download(self, bucket: str, key: str) -> bytes:
        obj_path = self._root / bucket / key
        if not obj_path.exists():
            raise FileNotFoundError(f"{bucket}/{key} not found in {self._root}")
        return obj_path.read_bytes()

    def delete(self, bucket: str, key: str) -> None:
        obj_path = self._root / bucket / key
        obj_path.unlink(missing_ok=True)

    def list_objects(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        bucket_dir = self._root / bucket
        if not bucket_dir.exists():
            return []
        keys = []
        for f in bucket_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(bucket_dir))
                if prefix is None or rel.startswith(prefix):
                    keys.append(rel)
        return sorted(keys)

    def get_uri(self, bucket: str, key: str) -> str:
        return f"file://{(self._root / bucket / key).resolve()}"
