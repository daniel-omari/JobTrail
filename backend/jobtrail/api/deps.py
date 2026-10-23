"""Request-scoped helpers: one SQLite connection per request, the inbox source, and the local AI (if running)."""
from __future__ import annotations

from collections.abc import Iterator
import sqlite3

from fastapi import Depends, Request

from .. import repo
from ..config import DEFAULT_MODEL
from ..db import connect
from ..pipeline.extract_llm import OllamaExtractor
from ..sources.base import InboxSource


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.config.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_source(request: Request) -> InboxSource:
    return request.app.state.source_factory()


def model_name(conn: sqlite3.Connection) -> str:
    return repo.get_settings(conn).get("model") or DEFAULT_MODEL


def get_llm(request: Request, conn: sqlite3.Connection = Depends(get_conn)) -> Iterator[OllamaExtractor | None]:
    """The local AI extractor, or None when Ollama/the model isn't available (rules-only mode)."""
    llm = request.app.state.llm_factory(model_name(conn))
    try:
        yield llm if (llm is not None and llm.available()) else None
    finally:
        if llm is not None:
            llm.close()
