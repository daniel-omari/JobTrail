"""Review queue: unknown senders whose SUBJECT looks hiring-related. Only headers are shown;
the body is read only if the user approves."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import repo
from ..logging_setup import message_hash
from ..models import ScanSummary
from ..pipeline.extract_llm import OllamaExtractor
from ..pipeline.gate import Gate
from ..pipeline.scan import open_and_process
from ..sources.base import InboxSource
from .deps import get_conn, get_llm, get_source

router = APIRouter(prefix="/api")


@router.get("/review")
def list_review(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return [{k: v for k, v in r.items() if k != "message_id"} for r in repo.review_list(conn)]


@router.post("/review/{rid}/approve")
def approve(
    rid: int,
    conn: sqlite3.Connection = Depends(get_conn),
    source: InboxSource = Depends(get_source),
    llm: OllamaExtractor | None = Depends(get_llm),
) -> dict:
    item = repo.review_get(conn, rid)
    if item is None:
        raise HTTPException(404, "Not in the review queue")
    header = next((h for h in source.list_headers() if h.id == item["message_id"]), None)
    repo.trust_sender(conn, item["sender"])  # learned: future emails from this sender are opened automatically
    repo.review_delete(conn, rid)
    if header is None:  # email no longer in the inbox
        conn.commit()
        return {"outcome": "gone"}
    settings = repo.get_settings(conn)
    summary = ScanSummary(mode="llm" if llm else "rules", defences=bool(settings["defences"]))
    outcome = open_and_process(conn, Gate(source, conn), header, "approved_by_you", summary, llm)
    return {"outcome": outcome}


@router.post("/review/{rid}/reject")
def reject(rid: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Never opened. The sender is remembered, so it isn't offered for review again."""
    item = repo.review_get(conn, rid)
    if item is None:
        raise HTTPException(404, "Not in the review queue")
    repo.reject_sender(conn, item["sender"])
    for message_id in repo.review_remove_sender(conn, item["sender"]):
        repo.mark_seen(conn, message_hash(message_id), "rejected_review")
    conn.commit()
    return {"outcome": "rejected"}
