# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import yaml
from pathlib import Path
from typing import Any, Dict, List
import logging

from k9_aif_abb.k9_core.persistence.base_persistence import (
    MemoryPersistence
)
from k9_aif_abb.k9_persistence.sqlite_persistence import SQLitePersistence

# Framework root (3 levels up: from k9_core/config/config_loader.py -> Framework/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger("ConfigLoader")


# ---------------------------------------------------------------------
# YAML Loader
# ---------------------------------------------------------------------
def load_yaml(path: str | Path) -> Dict[str, Any]:
    """Load YAML file into a dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------
# Persistence Wiring
# ---------------------------------------------------------------------
def _wire_persistence(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Attach persistence backend instance into config dict."""
    if "persistence" in cfg:
        persistence_cfg = cfg["persistence"]

        def resolve_path(db_path: str | Path) -> Path:
            path = Path(db_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            return path

        if isinstance(persistence_cfg, dict):
            backend = persistence_cfg.get("backend", "memory")
            if backend == "sqlite":
                db_path = persistence_cfg.get("db_path", "~/.k9_aif/k9_aif_state.db")
                cfg["persistence_backend"] = SQLitePersistence(resolve_path(db_path))
            elif backend == "memory":
                cfg["persistence_backend"] = MemoryPersistence()
            else:
                raise ValueError(f"Unsupported persistence backend: {backend}")

        elif isinstance(persistence_cfg, list):
            if persistence_cfg:  # pick first entry for ABB dry tests
                first = persistence_cfg[0]
                if first["name"] == "sqlite":
                    db_path = first.get("kwargs", {}).get("db_path", "~/.k9_aif/k9_aif_state.db")
                    cfg["persistence_backend"] = SQLitePersistence(resolve_path(db_path))
                elif first["name"] == "memory":
                    cfg["persistence_backend"] = MemoryPersistence()

        else:
            raise TypeError("Invalid persistence config format")

    return cfg


# ---------------------------------------------------------------------
# New: Orchestrator Loader (ABB + SBB merge)
# ---------------------------------------------------------------------
def _load_orchestrators(abb_path: Path, sbb_path: Path) -> List[Dict[str, Any]]:
    """Load and merge orchestrators.yaml from ABB and SBB."""
    orchestrators: List[Dict[str, Any]] = []

    for label, path in [("ABB", abb_path), ("SBB", sbb_path)]:
        if path.exists():
            try:
                data = load_yaml(path)
                added = data.get("orchestrators", [])
                orchestrators.extend(added)
                logger.info(f"[ConfigLoader] [INFO] Loaded {len(added)} {label} orchestrators from {path.name}")
            except Exception as e:
                logger.warning(f"[ConfigLoader] [WARN] Could not load {label} orchestrators: {e}")

    # Deduplicate by intent
    dedup = {}
    for o in orchestrators:
        dedup[o.get("intent")] = o
    return list(dedup.values())


# ---------------------------------------------------------------------
# Config Loaders
# ---------------------------------------------------------------------
def load_config(global_path: str | Path,
                flows_path: str | Path | None = None) -> Dict[str, Any]:
    """
    Load global config, optionally merge flows.yaml, and auto-wire persistence.
    - global_path: path to config.yaml
    - flows_path: optional path to flows.yaml
    """
    global_cfg = load_yaml(global_path)

    if flows_path:
        flows_cfg = load_yaml(flows_path)
        cfg = {**global_cfg, **flows_cfg}
    else:
        cfg = global_cfg

    # Wire persistence as before
    cfg = _wire_persistence(cfg)

    # Load ABB-only orchestrators if available
    abb_orch = BASE_DIR / "k9_aif_abb/config/orchestration.yaml"
    cfg["orchestrators"] = _load_orchestrators(abb_orch, Path())  # ABB-only mode
    return cfg


def load_app_config(app_name: str,
                    abb_config: str | Path = BASE_DIR / "k9_aif_abb/config/config.yaml",
                    sbb_config: str | Path | None = None,
                    flows_path: str | Path | None = None) -> Dict[str, Any]:
    """
    Load merged ABB + SBB config for a given app.
    - abb_config: global ABB config (system defaults)
    - sbb_config: optional app-specific config.yaml
    - flows_path: optional flows.yaml
    """
    cfg = load_yaml(abb_config)

    # Merge SBB config if provided
    if sbb_config is None:
        sbb_config = BASE_DIR / "k9_aif_demo" / app_name / "config/config.yaml"
    if Path(sbb_config).exists():
        app_cfg = load_yaml(sbb_config)
        cfg = {**cfg, **app_cfg}

    # Merge flows if any
    if flows_path is None:
        flows_path = BASE_DIR / "k9_aif_demo" / app_name / "config/flows.yaml"
    if Path(flows_path).exists():
        flows_cfg = load_yaml(flows_path)
        cfg = {**cfg, **flows_cfg}

    # Ensure log dirs
    logs_dir = Path(cfg.get("runtime", {}).get("logs_dir", "./logs"))
    app_log_dir = logs_dir / app_name
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_dir.mkdir(parents=True, exist_ok=True)

    # Wire persistence
    cfg = _wire_persistence(cfg)

    # Load orchestrators (ABB + SBB)
    abb_orch = BASE_DIR / "k9_aif_abb/config/orchestration.yaml"
    sbb_orch = BASE_DIR / f"k9_projects/{app_name}/config/orchestration.yaml"
    cfg["orchestrators"] = _load_orchestrators(abb_orch, sbb_orch)

    logger.info(f"[ConfigLoader] [OK] Loaded merged ABB + SBB config with {len(cfg['orchestrators'])} orchestrators")
    return cfg


# ---------------------------------------------------------------------
# Global CONFIG Singleton
# ---------------------------------------------------------------------
try:
    ABB_CONFIG_PATH = BASE_DIR / "k9_aif_abb/config/config.yaml"
    SBB_CONFIG_PATH = BASE_DIR / "k9_projects/sports_car_experience/config/config.yaml"

    if SBB_CONFIG_PATH.exists():
        CONFIG = load_app_config(
            app_name="sports_car_experience",
            abb_config=ABB_CONFIG_PATH,
            sbb_config=SBB_CONFIG_PATH
        )
    else:
        CONFIG = load_config(ABB_CONFIG_PATH)

    print(f"[ConfigLoader] [OK] Loaded merged config (ABB + SBB) from {ABB_CONFIG_PATH.name} + {SBB_CONFIG_PATH.name}")
except Exception as e:
    print(f"[ConfigLoader] [WARN] Warning: could not load merged config: {e}")
    CONFIG = {}