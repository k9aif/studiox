# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from pathlib import Path
from typing import Any, Dict


class BaseObjectStorage:
    """Base object storage with minimal local fallback."""

    def __init__(self, root: str = "object_store"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, bucket: str, key: str, data: bytes, metadata: Dict[str, Any] | None = None) -> None:
        bucket_dir = self.root / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        (bucket_dir / key).write_bytes(data)

    def download(self, bucket: str, key: str) -> bytes:
        return (self.root / bucket / key).read_bytes()

    def delete(self, bucket: str, key: str) -> None:
        (self.root / bucket / key).unlink(missing_ok=True)

    def list_objects(self, bucket: str, prefix: str | None = None) -> list[str]:
        bucket_dir = self.root / bucket
        if not bucket_dir.exists():
            return []
        return [f.name for f in bucket_dir.iterdir() if not prefix or f.name.startswith(prefix)]