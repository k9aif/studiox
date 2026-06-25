# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
k9_core.cache — ABB cache contract layer.

Provides the abstract ``BaseCache`` contract.
Concrete adapters live in ``k9_cache/adapters/``.

Typical import::

    from k9_aif_abb.k9_core.cache.base_cache import BaseCache
"""

from k9_aif_abb.k9_core.cache.base_cache import BaseCache

__all__ = ["BaseCache"]
