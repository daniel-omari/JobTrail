from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from .. import repo
from .deps import get_conn

router = APIRouter(prefix="/api")


@router.get("/applications")
def applications(archived: bool | None = False, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict]:
    apps = repo.list_applications(conn, archived=archived)
    for a in apps:
        a["history"] = repo.list_events(conn, a["id"])
    return apps
