# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Timer utilities for measuring execution stages in K9-AIF.
"""

import time
import logging
from functools import wraps

# Define MEASURE log level (between INFO and WARNING)
MEASURE_LEVEL = 25
logging.addLevelName(MEASURE_LEVEL, "MEASURE")

def measure(self, message, *args, **kwargs):
    if self.isEnabledFor(MEASURE_LEVEL):
        self._log(MEASURE_LEVEL, message, args, **kwargs)

logging.Logger.measure = measure


def timed_stage(stage_name: str, logger: logging.Logger, config: dict | None = None):
    """
    Decorator to measure execution time of a stage.
    - stage_name: label for the stage (e.g., "Governance PreCheck")
    - logger: the logger to use
    - config: runtime config dict (checks measurements.enabled)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Only measure if enabled in config
            if config and not config.get("runtime", {}).get("measurements", {}).get("enabled", False):
                return func(*args, **kwargs)

            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.measure(f"{stage_name} completed in {elapsed_ms:.2f} ms")
            return result
        return wrapper
    return decorator