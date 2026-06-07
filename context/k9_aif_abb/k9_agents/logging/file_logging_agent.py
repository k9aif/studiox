# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import logging
from k9_aif_abb.k9_core.logging.base_logger import BaseLoggingAgent

class FileLoggingAgent(BaseLoggingAgent):
    def __init__(self, name="FileLoggingAgent", logfile="logs/k9_aif.log"):
        super().__init__(name)
        logging.basicConfig(
            filename=logfile,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger(name)

    def log(self, message: str, level: str = "INFO"):
        print(f"[{self.name}] {level}: {message}")  # Console fallback
        self.logger.info(message)