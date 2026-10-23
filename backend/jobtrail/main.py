"""FastAPI app: JSON API under /api, the built React app at /, strict security headers on everything."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import applications, privacy, quarantine, scan, settings, status
from .config import Config
from .db import init_db
from .logging_setup import setup_logging
from .sources.base import InboxSource
from .pipeline.extract_llm import OllamaExtractor
from .sources.synthetic import SyntheticInbox

# The browser may only talk to this app itself: no CDNs, fonts, analytics or other sites.
CSP = (
    "default-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; "
    "style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; "
    "base-uri 'none'; form-action 'self'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def create_app(
    config: Config | None = None,
    source_factory: Callable[[], InboxSource] | None = None,
    llm_factory: Callable[[str], OllamaExtractor | None] | None = None,
) -> FastAPI:
    config = config or Config()
    init_db(config.db_path)
    setup_logging(config.log_path)

    # Interactive API docs are disabled: they load scripts from a CDN, which would break "nothing leaves the machine".
    app = FastAPI(title="JobTrail", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.config = config
    app.state.source_factory = source_factory or (lambda: SyntheticInbox(config.fixture_path))
    app.state.llm_factory = llm_factory or (lambda model: OllamaExtractor(config.ollama_url, model))

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    for module in (scan, applications, privacy, quarantine, settings, status):
        app.include_router(module.router)

    dist = config.frontend_dist
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse("<h1>JobTrail</h1><p>Frontend not built. Run <code>npm run build</code> in <code>frontend/</code>.</p>")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)

    return app
