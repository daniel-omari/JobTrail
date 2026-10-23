from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from .. import repo
from ..sources.base import InboxSource
from .deps import get_conn, get_source

router = APIRouter(prefix="/api")


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    defences: bool | None = None
    excluded_labels: list[str] | None = Field(default=None, max_length=50)
    scan_on_startup: bool | None = None
    auto_clean_days: int | None = Field(default=None, ge=7, le=3650)
    auto_clean_never: bool | None = None


@router.get("/settings")
def get_settings(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return repo.get_settings(conn)


@router.put("/settings")
def put_settings(update: SettingsUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    values = update.model_dump(exclude_none=True)
    if values.pop("auto_clean_never", False):
        values["auto_clean_days"] = None
    if "excluded_labels" in values:
        values["excluded_labels"] = sorted({s.strip() for s in values["excluded_labels"] if s.strip()})
    return repo.put_settings(conn, values)


@router.get("/labels")
def labels(source: InboxSource = Depends(get_source)) -> list[str]:
    """Label names present in the inbox (from headers only), to make excluding them easy."""
    return sorted({lbl for h in source.list_headers() for lbl in h.labels})
