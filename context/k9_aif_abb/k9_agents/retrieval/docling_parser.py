# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/retrieval/docling_parser.py

import asyncio
import httpx
import time
from pathlib import Path
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class DoclingParser(BaseAgent):
    """
    DoclingParser - Retrieval SBB
    -----------------------------
    Connects to a remote Docling-Serve API (e.g., running in a Podman container)
    to convert documents like PDFs into structured formats (Markdown, JSON, etc.).

    Features:
    - Config-driven endpoint discovery.
    - Auto-retry for transient connection issues.
    - Colored success logs for inference/parse success.
    """

    layer = "Retrieval SBB"

    def __init__(self, host: str = None, endpoint: str = None, config: dict | None = None):
        super().__init__(name="DoclingParser")

        # Resolve configuration from config.yaml
        if config and "retrieval" in config and "docling" in config["retrieval"]:
            conf = config["retrieval"]["docling"]
            self.host = conf.get("host", host or "http://localhost:5001")
            self.endpoint = conf.get("endpoint", endpoint or "/v1/convert/file")
        else:
            self.host = host or "http://localhost:5001"
            self.endpoint = endpoint or "/v1/convert/file"

        self.url = f"{self.host.rstrip('/')}{self.endpoint}"
        self.logger.info(f"[DoclingParser] Initialized - endpoint: {self.url}")

    # ------------------------------------------------------------------
    # Core Parse Routine
    # ------------------------------------------------------------------
    async def parse(self, file_path: str, max_retries: int = 3) -> dict:
        """Send a document to Docling-Serve and return structured output."""

        file_path = Path(file_path)
        assert file_path.exists(), f"File not found: {file_path}"

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    with open(file_path, "rb") as f:
                        files = {"files": (file_path.name, f, "application/pdf")}
                        self.logger.info(f"[DoclingParser] Attempt {attempt} -> POST {self.url}")
                        resp = await client.post(self.url, files=files)

                if resp.status_code != 200:
                    self.logger.warning(
                        f"[DoclingParser] HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                    return {"status": "error", "error": resp.text}

                data = resp.json()

                # Handle queued async responses
                if isinstance(data, dict) and "Task result not found" in str(data):
                    self.logger.warning(
                        "[DoclingParser] Task queued by Docling server - result not yet available"
                    )
                    return {"status": "queued", "message": data}

                # [OK] Successful parse - log in green
                print(f"\033[92m[K9-AIF][DoclingParser] [OK] Parse successful ({file_path.name})\033[0m")
                self.logger.info(f"[DoclingParser] Parse successful for '{file_path.name}'")
                return {"status": "ok", "data": data}

            except httpx.ConnectError as e:
                self.logger.error(f"[DoclingParser] Connection failed (attempt {attempt}): {e}")
                if attempt < max_retries:
                    wait = 2 ** (attempt - 1)
                    self.logger.warning(f"[DoclingParser] Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    return {"status": "connection_error", "error": str(e)}

            except Exception as e:
                self.logger.error(f"[DoclingParser] Unexpected error: {e}")
                return {"status": "error", "error": str(e)}

        return {"status": "error", "error": "Max retries exceeded"}

    # ------------------------------------------------------------------
    # Abstract method (required by BaseAgent)
    # ------------------------------------------------------------------
    def execute(self, *args, **kwargs):
        """Compatibility shim for ABB agent interface."""
        return {"status": "noop", "message": "Use parse(file_path) instead"}