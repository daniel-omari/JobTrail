"""Deleting data. Delete all wipes every table, then VACUUMs with secure_delete on, so removed text
doesn't linger in the database file's free pages."""
from __future__ import annotations

import sqlite3

from .db import ALL_TABLES


def delete_all(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA secure_delete = ON")
    for table in ALL_TABLES:
        conn.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed table names, not user input
    conn.commit()
    conn.execute("VACUUM")
