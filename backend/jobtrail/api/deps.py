"""Request-scoped helpers: one SQLite connection per request, and the configured inbox source."""
from __future__ import annotations

from collections.abc import Iterator
import sqlite3

from fastapi import Request

from ..db import connect
from ..sources.base import InboxSource


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.config.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_source(request: Request) -> InboxSource:
    return request.app.state.source_factory()
