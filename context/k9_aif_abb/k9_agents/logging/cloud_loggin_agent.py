# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from k9_aif_abb.k9_core.logging.base_logger import BaseLoggingAgent

class CloudLoggingAgent(BaseLoggingAgent):
    def log(self, message: str, level: str = "INFO"):
        print(f"[{self.name}] {level}: {message} (stubbed cloud logging)")