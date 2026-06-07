# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/formatter/base_formatter.py

import logging
import datetime
import os
import sys
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class BaseFormatterAgent(BaseAgent):
    """
    K9-AIF Formatter ABB - BaseFormatterAgent
    ----------------------------------------
    Provides a base for implementing data or log formatters.
    """

    layer = "Formatter ABB"

    def __init__(self, config=None, monitor=None, message_bus=None):
        # Pass all arguments to preserve BaseComponent contract
        super().__init__(
            config=config,
            name="BaseFormatterAgent",
            monitor=monitor,
            message_bus=message_bus,
        )

    async def execute(self, *args, **kwargs):
        await self.log("Executing formatter (stubbed implementation)", level="DEBUG")
        return {"result": "stubbed response from BaseFormatterAgent"}


class K9LoggingFormatter(logging.Formatter):
    """
    Dark-console friendly formatter for all K9-AIF logs, with configurable color.
    """

    COLOR_RESET   = "\033[0m"
    COLOR_GRAY    = "\033[90m"
    COLOR_GREEN   = "\033[92m"
    COLOR_CYAN    = "\033[96m"
    COLOR_MAGENTA = "\033[95m"
    COLOR_WHITE   = "\033[97m"

    def __init__(self, config: dict | None = None):
        super().__init__()

        env_color = os.getenv("K9AIF_LOG_COLOR", "").upper()
        yaml_color = (
            config.get("logging", {}).get("color")
            if isinstance(config, dict)
            else None
        )

        if env_color in ("ON", "TRUE", "1"):
            self.enable_color = True
        elif env_color in ("OFF", "FALSE", "0"):
            self.enable_color = False
        elif yaml_color is not None:
            self.enable_color = bool(yaml_color)
        else:
            self.enable_color = sys.stdout.isatty()

    def colorize(self, name: str, message: str) -> str:
        if not self.enable_color:
            return message

        name_upper = name.upper()
        if any(x in name_upper for x in ("LLM", "INFERENCE", "GUARDIAN")):
            return f"{self.COLOR_GREEN}{message}{self.COLOR_RESET}"
        elif "ORCHESTRATOR" in name_upper:
            return f"{self.COLOR_CYAN}{message}{self.COLOR_RESET}"
        elif "AGENT" in name_upper:
            return f"{self.COLOR_MAGENTA}{message}{self.COLOR_RESET}"
        else:
            return f"{self.COLOR_WHITE}{message}{self.COLOR_RESET}"

    def format(self, record: logging.LogRecord) -> str:
        ts_color = self.COLOR_GRAY if self.enable_color else ""
        ts_reset = self.COLOR_RESET if self.enable_color else ""
        ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")

        channel = record.name.upper().ljust(14)
        message = record.getMessage()
        colored_msg = self.colorize(channel, message)

        return f"{ts_color}{ts}{ts_reset} | {channel} | {colored_msg}"