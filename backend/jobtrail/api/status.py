from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from .. import repo
from ..pipeline.extract_llm import OllamaExtractor
from .deps import get_conn, get_llm, model_name

router = APIRouter(prefix="/api")


@router.get("/status")
def status(request: Request, conn: sqlite3.Connection = Depends(get_conn),
           llm: OllamaExtractor | None = Depends(get_llm)) -> dict:
    settings = repo.get_settings(conn)
    return {
        "ai_available": llm is not None,
        "mode": "llm" if llm else "rules",
        "demo": request.app.state.config.demo,
        "model": model_name(conn),
        "defences": bool(settings["defences"]),
        "review_count": conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0],
        "quarantine_count": conn.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0],
    }
