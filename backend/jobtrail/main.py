"""FastAPI app: JSON API under /api, the built React app at /, strict security headers on everything."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .api import applications, export, overview, privacy, quarantine, review, scan, settings, status
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
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "x-jobtrail"


def check_local_request(request: Request, config: Config) -> str | None:
    """Defend the local API against other websites open in the same browser.

    1. DNS rebinding: an attacker's domain can be made to resolve to 127.0.0.1, but the browser still sends
       the attacker's name in the Host header. Only our own host names are answered.
    2. CSRF: a malicious page can make the browser send a POST to 127.0.0.1. Every request that changes data
       must carry a custom X-JobTrail header. Browsers only let other sites add custom headers after a CORS
       preflight, which this app never approves. If an Origin header is present it must be ours as well.
    Returns a reason string when the request must be refused."""
    host = request.headers.get("host", "")
    if host not in config.allowed_hosts:
        return "Unexpected Host header"
    if request.method in UNSAFE_METHODS and request.url.path.startswith("/api"):
        if request.headers.get(CSRF_HEADER) != "1":
            return "Missing X-JobTrail header"
        origin = request.headers.get("origin")
        if origin is not None and origin not in config.allowed_origins:
            return "Cross-site request refused"
    return None


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
        reason = check_local_request(request, config)
        if reason:
            response: Response = JSONResponse({"detail": reason}, status_code=403)
        else:
            response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    for module in (scan, applications, export, overview, privacy, quarantine, review, settings, status):
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
