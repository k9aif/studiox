# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

class MessageAgent(BaseAgent):
    def __init__(self):
        super().__init__("MessageAgent")

    def execute(self, *args, **kwargs):
        print("[MessageAgent] Executing (stubbed)")
        return {"result": "stubbed response from MessageAgent"}
