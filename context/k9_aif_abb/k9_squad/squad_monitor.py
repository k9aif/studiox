# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import time


class DefaultSquadMonitor:

    def __init__(self):
        self.start_times = {}

    def on_squad_start(self, squad_id):
        print(f"[Squad {squad_id}] started")
        self.start_times[squad_id] = time.time()

    def on_agent_start(self, agent_id):
        print(f"  [Agent {agent_id}] started")

    def on_agent_end(self, agent_id):
        print(f"  [Agent {agent_id}] completed")

    def on_squad_end(self, squad_id):
        duration = time.time() - self.start_times.get(squad_id, time.time())
        print(f"[Squad {squad_id}] completed in {duration:.2f}s")