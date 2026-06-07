# SPDX-License-Identifier: Apache-2.0
# k9x_studio config service — reads/writes config.yaml

import os
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

_DEFAULTS: dict[str, Any] = {
    "llm": {
        "enabled": False,
        "provider": "ollama",
        "endpoint": "",
        "model": "granite3-dense:2b",
        # api_key is intentionally absent — secrets belong in .env only
    }
}


def _config_path() -> Path:
    env = os.environ.get("K9X_CONFIG_PATH", "").strip()
    if env:
        return Path(env)
    # backend/services/config_service.py → k9x_studio/config.yaml
    return Path(__file__).resolve().parent.parent.parent / "config.yaml"


def _load() -> dict:
    cfg: dict = {"llm": dict(_DEFAULTS["llm"])}
    path = _config_path()
    if not _HAS_YAML or not path.exists():
        return cfg
    try:
        with open(path) as f:
            data = _yaml.safe_load(f) or {}
        if isinstance(data.get("llm"), dict):
            cfg["llm"] = {**_DEFAULTS["llm"], **data["llm"]}
    except Exception:
        pass
    return cfg


def _save(cfg: dict) -> None:
    if not _HAS_YAML:
        return
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            _yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    except Exception:
        pass


def get_llm_config() -> dict:
    return _load()["llm"]


def is_llm_enabled() -> bool:
    cfg = get_llm_config()
    return bool(cfg.get("enabled") and cfg.get("endpoint", "").strip())


def update_llm_config(provider: str, endpoint: str, model: str) -> None:
    """Write non-sensitive LLM config to config.yaml. API keys belong in .env only."""
    cfg = _load()
    cfg["llm"] = {
        "enabled": bool(endpoint.strip()),
        "provider": provider.strip() or "ollama",
        "endpoint": endpoint.strip(),
        "model": model.strip() or "granite3-dense:2b",
    }
    _save(cfg)
