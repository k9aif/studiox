# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""SessionRegistry — named registry of K9SessionManager instances."""

import logging
from threading import Lock
from typing import Dict, Optional

from k9_aif_abb.k9_core.session.k9_session_manager import K9SessionManager


class SessionRegistry:
    """Static registry of named session managers."""

    _registry: Dict[str, K9SessionManager] = {}
    _lock = Lock()
    _logger = logging.getLogger("SessionRegistry")

    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError("SessionRegistry is static and cannot be instantiated")

    @staticmethod
    def register(name: str, manager: K9SessionManager) -> None:
        with SessionRegistry._lock:
            SessionRegistry._registry[name] = manager
            SessionRegistry._logger.info("[SessionRegistry] Registered: %s", name)

    @staticmethod
    def get(name: str) -> Optional[K9SessionManager]:
        return SessionRegistry._registry.get(name)

    @staticmethod
    def list_active() -> Dict[str, K9SessionManager]:
        return dict(SessionRegistry._registry)
