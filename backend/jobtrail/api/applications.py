from __future__ import annotations

import sqlite3
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .. import cleanup, repo
from ..models import Extraction, Status
from .deps import get_conn

router = APIRouter(prefix="/api")


class NewApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=120)
    status: Status = Status.APPLIED
    date: dt.date | None = None
    how_applied: str = Field(default="Added manually", max_length=120)


class EditApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=120)
    how_applied: str | None = Field(default=None, max_length=120)
    status: Status | None = None  # a stage change adds a dated event


def _with_history(conn, apps: list[dict]) -> list[dict]:
    for a in apps:
        a["history"] = repo.list_events(conn, a["id"])
    return apps


def _get_or_404(conn, app_id: int) -> dict:
    app = repo.get_application(conn, app_id)
    if app is None:
        raise HTTPException(404, "Application not found")
    return app


@router.get("/applications")
def applications(archived: bool | None = False, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    return _with_history(conn, repo.list_applications(conn, archived=archived))


@router.post("/applications")
def add(new: NewApplication, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    ex = Extraction(company=new.company.strip(), role=new.role.strip(), status=new.status)
    app_id = repo.record_event(conn, ex, new.date or dt.date.today(), "manual", new.how_applied, None, manual=True)
    conn.commit()
    return _with_history(conn, [_get_or_404(conn, app_id)])[0]


@router.patch("/applications/{app_id}")
def edit(app_id: int, change: EditApplication, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    app = _get_or_404(conn, app_id)
    repo.update_application(conn, app_id, change.company, change.role, change.how_applied)
    if change.status is not None and change.status.value != app["current_status"]:
        repo.add_stage(conn, app_id, change.status, dt.date.today())
    conn.commit()
    return _with_history(conn, [_get_or_404(conn, app_id)])[0]


@router.delete("/applications/{app_id}")
def delete(app_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    _get_or_404(conn, app_id)
    cleanup.delete_application(conn, app_id)
    return {"ok": True}


@router.post("/applications/{app_id}/do-not-track")
def do_not_track(app_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Remove it, and skip future emails about the same company + role."""
    app = _get_or_404(conn, app_id)
    repo.add_do_not_track(conn, app["company"], app["role"])
    cleanup.delete_application(conn, app_id)
    return {"ok": True}


@router.post("/applications/{app_id}/restore")
def restore(app_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    _get_or_404(conn, app_id)
    repo.restore_application(conn, app_id)
    conn.commit()
    return _with_history(conn, [_get_or_404(conn, app_id)])[0]


@router.post("/archive/clear")
def clear(older_than: int = 7, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    try:
        return {"removed": cleanup.clear_archive(conn, older_than)}
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/archive/force-clean")
def force_clean(confirm: bool = False, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    if not confirm:
        raise HTTPException(400, "Pass confirm=true: this also removes the last 7 days used by the UC export")
    return {"removed": cleanup.force_clean(conn)}
