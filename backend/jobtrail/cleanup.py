"""Deleting data.
- Clearing or deleting an application REDACTS its access-ledger lines: the date and rule stay (audit trail),
  the sender, subject and stored details go (privacy).
- Normal clears never touch anything with activity in the last 7 days, so this week's UC export stays intact.
- Delete all wipes every table, then VACUUMs with secure_delete on, so removed text doesn't linger in the file."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from .db import ALL_TABLES

MIN_KEEP_DAYS = 7


def _redact_and_delete(conn: sqlite3.Connection, app_ids: list[int]) -> int:
    if not app_ids:
        return 0
    marks = ",".join("?" * len(app_ids))
    hashes = [r[0] for r in conn.execute(
        f"SELECT message_hash FROM events WHERE application_id IN ({marks}) AND message_hash IS NOT NULL", app_ids)]
    if hashes:
        hmarks = ",".join("?" * len(hashes))
        conn.execute(
            f"UPDATE ledger SET sender=NULL, subject=NULL, stored_summary='record cleared by you', redacted=1 "
            f"WHERE message_hash IN ({hmarks})", hashes)
    conn.execute(f"DELETE FROM applications WHERE id IN ({marks})", app_ids)  # events cascade
    conn.commit()
    return len(app_ids)


def delete_application(conn: sqlite3.Connection, app_id: int) -> int:
    return _redact_and_delete(conn, [app_id])


def clear_archive(conn: sqlite3.Connection, older_than_days: int = MIN_KEEP_DAYS, today: date | None = None) -> int:
    """Remove archived applications whose most recent activity is older than N days (N is at least 7)."""
    if older_than_days < MIN_KEEP_DAYS:
        raise ValueError(f"older_than_days must be at least {MIN_KEEP_DAYS}")
    cutoff = ((today or date.today()) - timedelta(days=older_than_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT a.id FROM applications a JOIN events e ON e.application_id = a.id WHERE a.archived = 1 "
        "GROUP BY a.id HAVING MAX(e.event_date) < ?", (cutoff,))]
    return _redact_and_delete(conn, ids)


def force_clean(conn: sqlite3.Connection) -> int:
    """Remove the whole archive, including the last 7 days (the UI warns about the export first)."""
    ids = [r[0] for r in conn.execute("SELECT id FROM applications WHERE archived = 1")]
    return _redact_and_delete(conn, ids)


def delete_all(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA secure_delete = ON")
    for table in ALL_TABLES:
        conn.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed table names, not user input
    conn.commit()
    conn.execute("VACUUM")
