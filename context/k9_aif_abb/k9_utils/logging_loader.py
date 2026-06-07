# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# k9_utils/logging_loader.py

import os
from k9_aif_abb.k9_utils.config_loader import load_config
import logging

class FrameworkLogger:
    def __init__(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config.yaml"
        )
        cfg = load_config(config_path)
        level = cfg.get("logging", {}).get("level", "INFO")
        logging.basicConfig(level=getattr(logging, level.upper()))
        self.logger = logging.getLogger("K9-AIF")

    def log(self, message: str, level: str = "INFO"):
        getattr(self.logger, level.lower())(message)

# create global instance
framework_logger = FrameworkLogger()