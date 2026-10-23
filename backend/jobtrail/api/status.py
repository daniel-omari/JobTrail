from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from .. import repo
from .deps import get_conn

router = APIRouter(prefix="/api")


@router.get("/status")
def status(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    settings = repo.get_settings(conn)
    return {
        "ai_available": False,
        "mode": "rules",
        "model": None,
        "defences": bool(settings["defences"]),
        "review_count": conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0],
        "quarantine_count": conn.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0],
    }
