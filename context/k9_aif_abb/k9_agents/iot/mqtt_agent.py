# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import paho.mqtt.client as mqtt
from typing import Any, Dict
from k9_aif_abb.k9_core.iot.base_iot_agent import BaseIoTAgent


class MQTTAgent(BaseIoTAgent):
    """MQTT IoT agent implementation using Paho client."""

    def __init__(self, config=None):
        super().__init__(config)
        self.broker = self.config.get("broker", "localhost")
        self.port = self.config.get("port", 1883)
        self.client_id = self.config.get("client_id", "k9_aif_mqtt_client")
        self.client = mqtt.Client(client_id=self.client_id)

    def connect(self) -> bool:
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        self.log(f"Connected to MQTT broker at {self.broker}:{self.port}")
        return True

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        import json
        payload = json.dumps(message)
        self.client.publish(topic, payload)
        self.log(f"Published to {topic}: {payload}")

    def subscribe(self, topic: str, callback) -> None:
        def on_message(client, userdata, msg):
            self.log(f"Received message on {msg.topic}: {msg.payload.decode()}")
            callback(msg.topic, msg.payload.decode())

        self.client.subscribe(topic)
        self.client.on_message = on_message
        self.log(f"Subscribed to {topic}")

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
        self.log("Disconnected from MQTT broker")