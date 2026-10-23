"""Overview counts for a time range. Each count uses the date its event happened:
  sent        = applications whose FIRST event is in the range
  proceeding  = applications with an Assessment/Interview/Offer event in the range
  rejected    = applications with a Rejected/Closed event in the range
  active      = applications with any event in the range (the whole gauge)
The single gauge splits `active` by each application's CURRENT stage, so its segments add up:
  awaiting_now + proceeding_now + ended_now == active"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def range_bounds(rng: str, today: date | None = None) -> tuple[date | None, date]:
    today = today or date.today()
    if rng == "week":
        return today - timedelta(days=today.weekday()), today  # Monday to today
    if rng == "month":
        return today.replace(day=1), today
    return None, today  # all time


def overview(conn: sqlite3.Connection, rng: str, today: date | None = None) -> dict:
    start, end = range_bounds(rng, today)
    lo = start.isoformat() if start else "0000-01-01"
    hi = end.isoformat()

    def count(sql: str, *params) -> int:
        return conn.execute(sql, params).fetchone()[0]

    sent = count(
        "SELECT COUNT(*) FROM (SELECT application_id, MIN(event_date) AS first FROM events GROUP BY application_id) "
        "WHERE first BETWEEN ? AND ?", lo, hi)
    proceeding = count(
        "SELECT COUNT(DISTINCT application_id) FROM events WHERE status IN ('Assessment','Interview','Offer') "
        "AND event_date BETWEEN ? AND ?", lo, hi)
    rejected = count(
        "SELECT COUNT(DISTINCT application_id) FROM events WHERE status IN ('Rejected','Closed') "
        "AND event_date BETWEEN ? AND ?", lo, hi)
    active = count("SELECT COUNT(DISTINCT application_id) FROM events WHERE event_date BETWEEN ? AND ?", lo, hi)
    total = count("SELECT COUNT(*) FROM applications")
    by_status = dict(conn.execute(
        "SELECT current_status, COUNT(*) FROM applications WHERE id IN "
        "(SELECT DISTINCT application_id FROM events WHERE event_date BETWEEN ? AND ?) GROUP BY current_status",
        (lo, hi)).fetchall())
    return {
        "awaiting_now": by_status.get("Applied", 0),
        "proceeding_now": sum(by_status.get(s, 0) for s in ("Assessment", "Interview", "Offer")),
        "ended_now": sum(by_status.get(s, 0) for s in ("Rejected", "Closed")),
        "range": rng, "start": start.isoformat() if start else None, "end": hi,
        "sent": sent, "proceeding": proceeding, "rejected": rejected, "active": active, "total_all_time": total,
    }
