# K9 Core (ABBs)
Core abstract contracts used across K9-AIF.

## Base Classes
- `BaseAgent`: contract for all agents (`execute(payload)`).
- `BaseOrchestrator`: contract for orchestrators (`executeFlow(payload)`).
- `BaseRouter`: contract for routers (`route(payload)`, registry).

> You generally **do not subclass here** unless adding a new cross-framework contract.

Logging standard pattern:

Logger always initialized in base classes:
import logging
self.logger = logging.getLogger(self.name)

all logging calls use:

self.logger.info("...")
self.logger.debug("...")
self.logger.warning("...")
self.logger.error("...")