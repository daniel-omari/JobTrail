from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..models import ScanSummary
from ..pipeline.extract_llm import OllamaExtractor
from ..pipeline.scan import run_scan
from ..sources.base import InboxSource
from .deps import get_conn, get_llm, get_source

router = APIRouter(prefix="/api")


@router.post("/scan", response_model=ScanSummary)
def scan(
    conn: sqlite3.Connection = Depends(get_conn),
    source: InboxSource = Depends(get_source),
    llm: OllamaExtractor | None = Depends(get_llm),
) -> ScanSummary:
    return run_scan(conn, source, llm)
