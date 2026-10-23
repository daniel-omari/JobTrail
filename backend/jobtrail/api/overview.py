from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends

from ..overview import overview as compute
from .deps import get_conn

router = APIRouter(prefix="/api")


@router.get("/overview")
def overview(range: Literal["week", "month", "all"] = "week", conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return compute(conn, range)
