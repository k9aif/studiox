# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/streaming/redpanda_provider.py

import json
from kafka import KafkaConsumer
from k9_aif_abb.k9_core.streaming.base_stream_provider import BaseStreamProvider
from k9_aif_abb.k9_utils.config_loader import CONFIG


class RedpandaStreamProvider(BaseStreamProvider):
    """
    Governed group stream provider.
    Reads all runtime parameters (brokers, topic, log level)
    from the ABB config.yaml through the CONFIG loader.
    """

    def __init__(self, brokers: str | None = None):
        # Load messaging configuration from governed CONFIG
        msg_cfg = CONFIG.get("messaging", {})
        self.brokers = brokers or ",".join(msg_cfg.get("brokers", ["192.168.1.98:9092"]))
        self.topic = msg_cfg.get("topic", "k9aif-events")
        self.security_protocol = msg_cfg.get("security_protocol", "PLAINTEXT")
        self.log_level = (
            CONFIG.get("logging", {}).get("level", "INFO").upper()
        )

    # ---------------------------------------------------------------
    # Optional connection check
    # ---------------------------------------------------------------
    def connect(self):
        if self.log_level == "DEBUG":
            print(f"[RedpandaStreamProvider] Connected -> {self.brokers}")

    # ---------------------------------------------------------------
    # Subscribe to live topic stream
    # ---------------------------------------------------------------
    def subscribe(self, topic: str | None, group_id: str, on_message):
        topic = topic or self.topic
        if self.log_level == "DEBUG":
            print(f"[RedpandaStreamProvider] Subscribing to topic='{topic}' "
                  f"(brokers={self.brokers}, group={group_id})")

        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[self.brokers],
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id=group_id,
                security_protocol=self.security_protocol,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            print(f"[RedpandaStreamProvider] Listening on topic={topic}, group_id={group_id}")
            
            for msg in consumer:
                value = msg.value
                if self.log_level == "DEBUG":
                    print(f"[RedpandaStreamProvider] Received -> {value}")
                on_message(value)

        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"[RedpandaStreamProvider] [ERROR] Error: {e}\n{trace}")