# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/logging/log_setup.py

import logging, os, yaml
from pathlib import Path
from logging.handlers import RotatingFileHandler
from k9_aif_abb.k9_core.formatter.base_formatter import K9LoggingFormatter


def setup_logging(app_name: str | None = None,
                  app_config: dict | None = None,
                  runtime_config_path: str = "config/runtime.yaml"):
    """
    Initialize K9-AIF logging system.

    Resolution order for key settings:
      - Level:    env K9AIF_LOG_LEVEL -> app_config['logging']['level'] -> INFO
      - Color:    env K9AIF_LOG_COLOR -> app_config['logging']['color'] -> auto
      - Dir:      app_config['logging']['dir'] -> runtime.yaml -> ./logs/<app_name>
    """

    # ----------------------------
    # 1. Determine log level
    # ----------------------------
    env_level = os.getenv("K9AIF_LOG_LEVEL")
    yaml_level = (
        app_config.get("logging", {}).get("level")
        if isinstance(app_config, dict)
        else None
    )
    log_level_name = (env_level or yaml_level or "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # ----------------------------
    # 2. Determine logs directory
    # ----------------------------
    cwd = Path.cwd()
    logs_dir = None

    if app_config and "logging" in app_config:
        logs_dir = app_config["logging"].get("dir")

    if not logs_dir and os.path.exists(runtime_config_path):
        with open(runtime_config_path) as f:
            cfg = yaml.safe_load(f) or {}
        logs_dir = cfg.get("runtime", {}).get("logs_dir")

    if not logs_dir:
        logs_dir = f"logs/{app_name}" if app_name else "logs"

    logs_dir = Path(logs_dir)
    if not logs_dir.is_absolute():
        logs_dir = cwd / logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # 3. Initialize formatters
    # ----------------------------
    fmt = K9LoggingFormatter(config=app_config)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # allow fine-grained filtering downstream

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(log_level)
    root_logger.addHandler(ch)

    # File handler
    log_filename = f"{app_name}.log" if app_name else "k9_aif.log"

    fh = RotatingFileHandler(
        logs_dir / log_filename, maxBytes=2_000_000, backupCount=5
    )

    fh.setFormatter(K9LoggingFormatter(config={**(app_config or {}), "logging": {"color": False}}))  # file logs = no color
    fh.setLevel(log_level)
    root_logger.addHandler(fh)

    # Governance-specific logger
    gov_logger = logging.getLogger("governance")
    gov_logger.setLevel(logging.INFO)
    gov_file = RotatingFileHandler(
        logs_dir / "governance.log", maxBytes=2_000_000, backupCount=5
    )
    gov_file.setFormatter(K9LoggingFormatter(config={"logging": {"color": False}}))
    gov_logger.addHandler(gov_file)

    print(f"K9-AIF logging initialized -> level={log_level_name}, dir={logs_dir}")
    return logs_dir