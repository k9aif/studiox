# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import abstractmethod
from k9_aif_abb.k9_core.messaging.base_message import BaseMessageAgent


class TopicMessageAgent(BaseMessageAgent):

    @abstractmethod
    def publish(self, message: dict):
        """Publish a message to the topic"""
        pass

    @abstractmethod
    def subscribe(self, callback):
        """Subscribe to a topic with a callback"""
        pass