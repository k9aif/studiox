# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Utilities Package

The `k9_utils` package provides shared utility functions and helper components
used across the K9-AIF framework.

These utilities support common concerns such as configuration loading,
logging setup, timing, transformation, and auxiliary processing.


## Key Responsibilities

- Configuration loading and parsing
- Logging initialization and setup
- Timing and performance utilities
- Data transformation helpers (XML/JSON)
- Miscellaneous support utilities


## Architectural Positioning

The utilities package supports all layers of K9-AIF but does not define
core architectural building blocks.

It provides reusable helper functions that simplify implementation while
keeping the core architecture clean and focused.


## Architectural Note

> k9_utils provides supporting helper functions, while core framework packages define architectural behavior.

"""