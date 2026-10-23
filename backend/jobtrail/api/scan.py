from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..models import ScanSummary
from ..pipeline.scan import run_scan
from ..sources.base import InboxSource
from .deps import get_conn, get_source

router = APIRouter(prefix="/api")


@router.post("/scan", response_model=ScanSummary)
def scan(conn: sqlite3.Connection = Depends(get_conn), source: InboxSource = Depends(get_source)) -> ScanSummary:
    return run_scan(conn, source)
