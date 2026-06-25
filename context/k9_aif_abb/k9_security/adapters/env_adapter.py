# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
EnvSecretAdapter — default secret manager that reads from environment variables.

This is the zero-dependency, zero-config default.  All K9-AIF apps use this
adapter out of the box — secrets are placed in ``.env`` (loaded via
``python-dotenv`` or the container environment) and never written to config.yaml.

YAML config (no extra keys required)::

    secrets:
      provider: env          # default when 'secrets' block is absent

SBB extension example::

    class PrefixedEnvAdapter(EnvSecretAdapter):
        def __init__(self, config=None):
            super().__init__(config)
            self._prefix = (config or {}).get("env_prefix", "K9_")

        def get(self, key):
            return super().get(f"{self._prefix}{key}")
"""

import os
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.security.base_secret_manager import BaseSecretManager


class EnvSecretAdapter(BaseSecretManager):
    """Reads secrets from ``os.environ``."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}

    def get(self, key: str) -> str:
        """
        Return the environment variable named *key*.

        Raises:
            KeyError: when the variable is absent or empty.
        """
        value = os.environ.get(key)
        if not value:
            raise KeyError(key)
        return value
