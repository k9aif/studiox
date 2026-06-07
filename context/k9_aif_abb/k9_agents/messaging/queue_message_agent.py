# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import abstractmethod
from k9_aif_abb.k9_core.messaging.base_message import BaseMessageAgent

class QueueMessageAgent(BaseMessageAgent):

    @abstractmethod
    def send(self, message: dict):
        """Send a message to the queue"""
        pass

    @abstractmethod
    def receive(self) -> dict:
        """Receive a message from the queue"""
        pass