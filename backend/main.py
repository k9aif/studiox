# SPDX-License-Identifier: Apache-2.0
# k9x_studio backend — FastAPI entry point

import sys
from pathlib import Path

# Make sure `backend` package is importable when run from k9x_studio/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env from studio root if present
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from backend.api.routes import router as api_router

app = FastAPI(
    title="k9x_studio",
    description="K9-AIF Visual Architecture Builder",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Serve built React frontend when dist/ exists (production / container mode)
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    # Standalone "how the studio is built" page (vite copies public/architecture/
    # into dist/architecture/ verbatim — mount it before the SPA catch-all so it
    # serves the real static page instead of falling through to index.html)
    _ARCH_DIR = _DIST / "architecture"
    if _ARCH_DIR.exists():
        app.mount("/architecture", StaticFiles(directory=str(_ARCH_DIR), html=True), name="architecture")

    # Pre-generated template class diagrams (vite copies frontend/public/class-diagrams/
    # into dist/class-diagrams/ verbatim) — mount before the SPA catch-all so .svg/.puml
    # requests get the real files instead of index.html.
    _CLASS_DIAGRAMS_DIR = _DIST / "class-diagrams"
    if _CLASS_DIAGRAMS_DIR.exists():
        app.mount("/class-diagrams", StaticFiles(directory=str(_CLASS_DIAGRAMS_DIR)), name="class-diagrams")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        return HTMLResponse((_DIST / "index.html").read_text())
else:
    @app.get("/")
    def root():
        return {"message": "k9x_studio backend running — connect via frontend on :5173"}
