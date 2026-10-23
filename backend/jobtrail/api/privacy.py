from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repo
from ..cleanup import delete_all as _delete_all
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


@router.post("/delete-all")
def delete_all(confirm: bool = False, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    if not confirm:
        raise HTTPException(400, "Pass confirm=true to delete everything")
    _delete_all(conn)
    return {"ok": True}
