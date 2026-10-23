from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from .. import repo
from .deps import get_conn

router = APIRouter(prefix="/api")


@router.get("/ledger")
def ledger(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    last = conn.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1").fetchone()
    totals = conn.execute("SELECT COALESCE(SUM(skipped),0) AS skipped FROM scan_runs").fetchone()
    return {
        "entries": repo.ledger_list(conn),
        "skipped_unopened_total": totals["skipped"],
        "last_scan": dict(last) if last else None,
    }
