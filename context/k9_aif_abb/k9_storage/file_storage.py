# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/storage/file_storage.py

from pathlib import Path
from typing import Any
from k9_aif_abb.k9_core.storage.base_storage import BaseStorage

class LocalFileStorage(BaseStorage):
    """
    Simple local file system storage.
    Keys are file paths relative to base_dir.
    """

    def __init__(self, base_dir: str | Path = "k9_storage", **kwargs):
        super().__init__(name="LocalFileStorage", config=kwargs)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        return self.base_dir / key

    def save(self, key: str, data: Any) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else str(data))

    def load(self, key: str) -> str:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        return path.read_text(encoding="utf-8")

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()