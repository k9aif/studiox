# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/streaming_factory.py

from k9_aif_abb.k9_core.streaming.redpanda_provider import RedpandaStreamProvider


class StreamingFactory:
    """
    StreamingFactory
    ----------------
    Centralized registry for streaming backends used by ABB/SBB layers.
    Supports multiple aliases ('redpanda', 'kafka', 'redpanda_logs') that
    all map to the governed RedpandaStreamProvider for the unified event bus.
    """

    _registry = {
        "redpanda_logs": RedpandaStreamProvider,
        "redpanda": RedpandaStreamProvider,   
        "kafka": RedpandaStreamProvider,      
    }

    @staticmethod
    def get(name: str, **kwargs):
        """
        Retrieve a configured stream provider instance.

        Args:
            name (str): The provider key ('redpanda_logs', 'redpanda', 'kafka')
            **kwargs: Additional parameters to pass to the provider class.

        Returns:
            BaseStreamProvider: Initialized provider instance.

        Raises:
            ValueError: If the provider name is not recognized.
        """
        if not name:
            name = "redpanda_logs"

        # Normalize name and aliases
        name = name.lower().strip()
        if name in ("kafka", "redpanda"):
            name = "redpanda_logs"

        if name not in StreamingFactory._registry:
            raise ValueError(f"Unknown stream provider: {name}")

        provider_cls = StreamingFactory._registry[name]
        return provider_cls(**kwargs)