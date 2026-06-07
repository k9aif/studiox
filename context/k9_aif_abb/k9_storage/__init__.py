# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Storage Package

The `k9_storage` package provides storage-oriented framework components within
the K9-AIF architecture.

It builds on the `BaseStorage` abstraction defined in `k9_core` and includes
reusable storage implementations for database, file, and object-based storage.

These implementations serve as default framework storage components and may be
used directly, extended, or replaced by downstream Solution Building Blocks
(SBBs) as needed.


## Key Responsibilities

- Providing reusable storage implementations based on `BaseStorage`
- Supporting database, file, and object storage patterns
- Enabling pluggable storage backends
- Serving as the physical storage layer beneath persistence and retrieval
- Allowing downstream SBBs to extend or replace storage implementations


## Typical Components

This package may include:

- `database_storage` — database-oriented storage implementation
- `file_storage` — file-based storage implementation
- `object_storage` — object store implementation


## Example: Extending BaseStorage

    from k9_aif_abb.k9_core.storage.base_storage import BaseStorage

    class MyCustomStorage(BaseStorage):
        def save(self, key, value):
            pass

        def load(self, key):
            pass

"""