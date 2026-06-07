# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from k9_aif_abb.k9_core.presentation.base_ui import BaseUI

class WebUI(BaseUI):
    def render(self, response: dict) -> None:
        print("[WebUI] Rendering response (stubbed):", response)