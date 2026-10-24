from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repo
from ..cleanup import delete_all as _delete_all
from ..cleanup import reset_scan_data as _reset_scan_data
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


@router.post("/reset-scan-data")
def reset_scan_data(confirm: bool = False, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    if not confirm:
        raise HTTPException(400, "Pass confirm=true to reset scan data")
    _reset_scan_data(conn)
    return {"ok": True}


@router.get("/everything")
def everything(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Every item JobTrail stores, grouped by type. Nothing is held anywhere else."""
    apps = repo.list_applications(conn)
    for a in apps:
        a["history"] = repo.list_events(conn, a["id"])
    trusted, rejected = repo.sender_lists(conn)
    return {
        "applications": apps,
        "ledger": repo.ledger_list(conn),
        "review_queue": [{k: v for k, v in r.items() if k != "message_id"} for r in repo.review_list(conn)],
        "quarantine": [{"sender": q["sender"], "subject": q["subject"], "received_date": q["received_date"],
                        "reasons": [{"reason": r["reason"], "excerpt": r["excerpt"]} for r in q["reasons"]]}
                       for q in repo.quarantine_list(conn)],
        "trusted_senders": sorted(trusted),
        "rejected_senders": sorted(rejected),
        "do_not_track": [{"company": c, "role": r} for c, r in repo.do_not_track_list(conn)],
        "settings": repo.get_settings(conn),
        "processed_email_fingerprints": conn.execute("SELECT COUNT(*) FROM seen_messages").fetchone()[0],
        "scan_runs": [dict(r) for r in conn.execute(
            "SELECT ran_at, checked, opened, skipped, review, quarantined, mode, defences FROM scan_runs ORDER BY id DESC")],
    }
