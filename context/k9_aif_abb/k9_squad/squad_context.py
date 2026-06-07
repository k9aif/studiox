# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

class SquadContext:
    """
    Shared working state for agents inside a squad.
    """

    def __init__(self, initial_data=None):
        self.data = initial_data or {}
        self.agent_outputs = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def add_agent_output(self, agent_name, output):
        self.agent_outputs[agent_name] = output

    def get_agent_output(self, agent_name):
        return self.agent_outputs.get(agent_name)