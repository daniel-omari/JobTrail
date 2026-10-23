from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from .. import repo
from ..logging_setup import message_hash
from ..models import Extraction
from ..pipeline import rules
from ..pipeline.scan import stored_summary
from ..sources.base import Header
from .deps import get_conn

router = APIRouter(prefix="/api")


@router.get("/quarantine")
def list_quarantine(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    items = repo.quarantine_list(conn)
    for i in items:
        i.pop("message_id", None)  # internal id, not needed by the UI
    return items


@router.post("/quarantine/{qid}/release")
def release(qid: int, fields: Extraction, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Save the email to the Tracker using fields the USER confirmed (pre-filled from rules, never from the AI)."""
    item = repo.quarantine_get(conn, qid)
    if item is None:
        raise HTTPException(404, "Not in quarantine")
    header = Header(id=item["message_id"], sender=item["sender"], display_name="", subject=item["subject"],
                    date=date.fromisoformat(item["received_date"]))
    source = rules.platform_for(header) or header.domain
    app_id = repo.record_event(conn, fields, header.date, source, rules.how_applied(source), message_hash(header.id))
    if item["ledger_id"]:
        repo.ledger_set_stored(conn, item["ledger_id"], "released by you: " + stored_summary(fields))
    repo.mark_seen(conn, message_hash(header.id), "opened")
    repo.quarantine_delete(conn, qid)
    conn.commit()
    return {"application_id": app_id}


@router.post("/quarantine/{qid}/discard")
def discard(qid: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    item = repo.quarantine_get(conn, qid)
    if item is None:
        raise HTTPException(404, "Not in quarantine")
    if item["ledger_id"]:
        repo.ledger_set_stored(conn, item["ledger_id"], "quarantined, then discarded by you: nothing stored")
    repo.quarantine_delete(conn, qid)
    conn.commit()
    return {"ok": True}
