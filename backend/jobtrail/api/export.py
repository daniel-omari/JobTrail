from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .. import export
from .deps import get_conn

router = APIRouter(prefix="/api")


@router.get("/export")
def get_export(start: date | None = None, end: date | None = None, format: str = "text",
               conn: sqlite3.Connection = Depends(get_conn)):
    d_start, d_end = export.default_range()
    start, end = start or d_start, end or d_end
    if start > end or (end - start).days > 366:
        raise HTTPException(422, "Choose a range of up to a year, with the start before the end")
    if format == "csv":
        return Response(
            export.csv_text(conn, start, end), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="jobtrail-{start}-to-{end}.csv"'},
        )
    return {"start": start.isoformat(), "end": end.isoformat(), "count": len(export.rows(conn, start, end)),
            "text": export.summary_text(conn, start, end)}
