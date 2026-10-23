"""Tasks run once when JobTrail starts (before the browser opens):
1. Auto-clean: remove archived entries older than the user's setting (default 90 days; never the last 7; can be off).
2. Scan on startup: if enabled, fetch the latest updates so the app opens up to date."""
from __future__ import annotations

from collections.abc import Callable

from . import cleanup, repo
from .config import DEFAULT_MODEL, Config
from .db import connect, init_db
from .logging_setup import get_logger
from .pipeline.extract_llm import OllamaExtractor
from .pipeline.scan import run_scan
from .sources.base import InboxSource


def run_startup_tasks(
    config: Config,
    source_factory: Callable[[], InboxSource],
    llm_factory: Callable[[str], OllamaExtractor | None],
) -> dict:
    init_db(config.db_path)
    conn = connect(config.db_path)
    result: dict = {"auto_cleaned": 0, "scanned": False}
    try:
        settings = repo.get_settings(conn)
        days = settings.get("auto_clean_days")
        if days:
            result["auto_cleaned"] = cleanup.clear_archive(conn, max(int(days), cleanup.MIN_KEEP_DAYS))
        if settings.get("scan_on_startup"):
            llm = llm_factory(settings.get("model") or DEFAULT_MODEL)
            try:
                summary = run_scan(conn, source_factory(), llm if (llm and llm.available()) else None)
            finally:
                if llm:
                    llm.close()
            result["scanned"] = True
            result["summary"] = summary.model_dump()
    finally:
        conn.close()
    get_logger().info("startup auto_cleaned=%s scanned=%s", result["auto_cleaned"], result["scanned"])
    return result
