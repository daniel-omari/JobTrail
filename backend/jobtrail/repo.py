"""All SQL lives here, so it's one place to read to know what is stored."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone

from .models import ENDED, Extraction, Status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- settings ----------

DEFAULT_SETTINGS: dict[str, object] = {
    "defences": True,
    "excluded_labels": [],
    "scan_on_startup": False,
    "auto_clean_days": 90,
    "model": None,  # None -> config.DEFAULT_MODEL
}


def get_settings(conn: sqlite3.Connection) -> dict:
    out = dict(DEFAULT_SETTINGS)
    for row in conn.execute("SELECT key, value FROM settings"):
        out[row["key"]] = json.loads(row["value"])
    return out


def put_settings(conn: sqlite3.Connection, values: dict) -> dict:
    for key, value in values.items():
        if key not in DEFAULT_SETTINGS:
            raise KeyError(key)
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )
    conn.commit()
    return get_settings(conn)


# ---------- seen messages ----------

def seen_outcome(conn: sqlite3.Connection, msg_hash: str) -> str | None:
    row = conn.execute("SELECT outcome FROM seen_messages WHERE message_hash=?", (msg_hash,)).fetchone()
    return row["outcome"] if row else None


def mark_seen(conn: sqlite3.Connection, msg_hash: str, outcome: str) -> None:
    conn.execute(
        "INSERT INTO seen_messages(message_hash, outcome) VALUES(?, ?) "
        "ON CONFLICT(message_hash) DO UPDATE SET outcome=excluded.outcome",
        (msg_hash, outcome),
    )


# ---------- ledger ----------

def ledger_insert(conn: sqlite3.Connection, msg_hash: str, sender: str, subject: str, rule: str) -> int:
    cur = conn.execute(
        "INSERT INTO ledger(opened_at, message_hash, sender, subject, rule, stored_summary) VALUES(?,?,?,?,?,?)",
        (_now(), msg_hash, sender, subject, rule, "pending"),
    )
    conn.commit()  # committed before the body is read: the record exists even if processing crashes
    return int(cur.lastrowid)


def ledger_set_stored(conn: sqlite3.Connection, ledger_id: int, stored_summary: str) -> None:
    conn.execute("UPDATE ledger SET stored_summary=? WHERE id=?", (stored_summary, ledger_id))


def ledger_list(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM ledger ORDER BY id DESC").fetchall()
    return [dict(r) | {"redacted": bool(r["redacted"])} for r in rows]


def ledger_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


# ---------- applications ----------

def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def find_application(conn: sqlite3.Connection, company: str, role: str) -> sqlite3.Row | None:
    for row in conn.execute("SELECT * FROM applications"):
        if _norm(row["company"]) == _norm(company) and _norm(row["role"]) == _norm(role):
            return row
    return None


def record_event(
    conn: sqlite3.Connection,
    extraction: Extraction,
    event_date: date,
    source: str,
    how_applied: str,
    msg_hash: str | None,
    manual: bool = False,
) -> int:
    """Create or update an application and append a status event. Returns application id."""
    now = _now()
    app = find_application(conn, extraction.company, extraction.role)
    if app is None:
        cur = conn.execute(
            "INSERT INTO applications(company, role, source, how_applied, current_status, archived, manual, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (extraction.company, extraction.role, source, how_applied, extraction.status.value,
             int(extraction.status in ENDED), int(manual), now, now),
        )
        app_id = int(cur.lastrowid)
    else:
        app_id = int(app["id"])
    conn.execute(
        "INSERT INTO events(application_id, status, event_date, message_hash) VALUES(?,?,?,?)",
        (app_id, extraction.status.value, event_date.isoformat(), msg_hash),
    )
    _refresh_current_status(conn, app_id)
    return app_id


def _refresh_current_status(conn: sqlite3.Connection, app_id: int) -> None:
    """Current status = the latest event by date (ties: latest inserted). Ended apps move to the archive."""
    latest = conn.execute(
        "SELECT status FROM events WHERE application_id=? ORDER BY event_date DESC, id DESC LIMIT 1", (app_id,)
    ).fetchone()
    if latest is None:
        return
    status = Status(latest["status"])
    conn.execute(
        "UPDATE applications SET current_status=?, archived=?, updated_at=? WHERE id=?",
        (status.value, int(status in ENDED), _now(), app_id),
    )


def list_applications(conn: sqlite3.Connection, archived: bool | None = None) -> list[dict]:
    sql = (
        "SELECT a.*, MIN(e.event_date) AS applied_date, MAX(e.event_date) AS last_update "
        "FROM applications a LEFT JOIN events e ON e.application_id = a.id"
    )
    params: tuple = ()
    if archived is not None:
        sql += " WHERE a.archived = ?"
        params = (int(archived),)
    sql += " GROUP BY a.id ORDER BY last_update DESC, a.id DESC"
    out = []
    for r in conn.execute(sql, params):
        d = dict(r)
        d["archived"] = bool(d["archived"])
        d["manual"] = bool(d["manual"])
        out.append(d)
    return out


def list_events(conn: sqlite3.Connection, app_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT status, event_date FROM events WHERE application_id=? ORDER BY event_date, id", (app_id,)
    )]


# ---------- review queue ----------

def review_add(conn: sqlite3.Connection, message_id: str, sender: str, subject: str, received: date) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO review_queue(message_id, sender, subject, received_date) VALUES(?,?,?,?)",
        (message_id, sender, subject, received.isoformat()),
    )


def review_list(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM review_queue ORDER BY received_date DESC, id DESC")]


# ---------- quarantine ----------

def quarantine_add(conn, message_id, sender, subject, received: date, reasons: list[dict], prefill: dict, ledger_id) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO quarantine(message_id, sender, subject, received_date, reasons, rules_prefill, ledger_id)"
        " VALUES(?,?,?,?,?,?,?)",
        (message_id, sender, subject, received.isoformat(), json.dumps(reasons), json.dumps(prefill), ledger_id),
    )


def quarantine_list(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM quarantine ORDER BY received_date DESC, id DESC"):
        d = dict(r)
        d["reasons"] = json.loads(d["reasons"])
        d["rules_prefill"] = json.loads(d["rules_prefill"])
        out.append(d)
    return out


# ---------- senders ----------

def sender_lists(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    trusted = {r[0] for r in conn.execute("SELECT address FROM trusted_senders")}
    rejected = {r[0] for r in conn.execute("SELECT address FROM rejected_senders")}
    return trusted, rejected


def do_not_track_list(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    return [(r["company"], r["role"]) for r in conn.execute("SELECT company, role FROM do_not_track")]


# ---------- scan runs ----------

def scan_run_add(conn: sqlite3.Connection, s) -> None:
    conn.execute(
        "INSERT INTO scan_runs(ran_at, checked, opened, skipped, review, quarantined, mode, defences) VALUES(?,?,?,?,?,?,?,?)",
        (_now(), s.checked, s.opened, s.skipped, s.review, s.quarantined, s.mode, int(s.defences)),
    )


def quarantine_get(conn: sqlite3.Connection, qid: int) -> dict | None:
    r = conn.execute("SELECT * FROM quarantine WHERE id=?", (qid,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["reasons"] = json.loads(d["reasons"])
    d["rules_prefill"] = json.loads(d["rules_prefill"])
    return d


def quarantine_delete(conn: sqlite3.Connection, qid: int) -> None:
    conn.execute("DELETE FROM quarantine WHERE id=?", (qid,))


def review_get(conn: sqlite3.Connection, rid: int) -> dict | None:
    r = conn.execute("SELECT * FROM review_queue WHERE id=?", (rid,)).fetchone()
    return dict(r) if r else None


def review_remove_sender(conn: sqlite3.Connection, sender: str) -> list[str]:
    ids = [r["message_id"] for r in conn.execute("SELECT message_id FROM review_queue WHERE sender=?", (sender,))]
    conn.execute("DELETE FROM review_queue WHERE sender=?", (sender,))
    return ids


def review_delete(conn: sqlite3.Connection, rid: int) -> None:
    conn.execute("DELETE FROM review_queue WHERE id=?", (rid,))


def trust_sender(conn: sqlite3.Connection, address: str) -> None:
    conn.execute("INSERT OR IGNORE INTO trusted_senders(address) VALUES(?)", (address,))
    conn.execute("DELETE FROM rejected_senders WHERE address=?", (address,))


def reject_sender(conn: sqlite3.Connection, address: str) -> None:
    conn.execute("INSERT OR IGNORE INTO rejected_senders(address) VALUES(?)", (address,))
    conn.execute("DELETE FROM trusted_senders WHERE address=?", (address,))


def get_application(conn: sqlite3.Connection, app_id: int) -> dict | None:
    for a in list_applications(conn):
        if a["id"] == app_id:
            return a
    return None


def update_application(conn: sqlite3.Connection, app_id: int, company: str | None, role: str | None,
                       how_applied: str | None) -> None:
    sets, params = [], []
    for col, val in (("company", company), ("role", role), ("how_applied", how_applied)):
        if val is not None:
            sets.append(f"{col}=?")
            params.append(val)
    if sets:
        sets.append("updated_at=?")
        params += [_now(), app_id]
        conn.execute(f"UPDATE applications SET {', '.join(sets)} WHERE id=?", params)  # noqa: S608 - fixed columns


def add_stage(conn: sqlite3.Connection, app_id: int, status: Status, on: date) -> None:
    conn.execute("INSERT INTO events(application_id, status, event_date, message_hash) VALUES(?,?,?,NULL)",
                 (app_id, status.value, on.isoformat()))
    _refresh_current_status(conn, app_id)


def restore_application(conn: sqlite3.Connection, app_id: int) -> None:
    """A misfiled rejection/closure: remove the ending event(s) and return the application to the active list."""
    conn.execute("DELETE FROM events WHERE application_id=? AND status IN ('Rejected','Closed')", (app_id,))
    if conn.execute("SELECT COUNT(*) FROM events WHERE application_id=?", (app_id,)).fetchone()[0] == 0:
        conn.execute("INSERT INTO events(application_id, status, event_date, message_hash) VALUES(?,?,?,NULL)",
                     (app_id, Status.APPLIED.value, date.today().isoformat()))
    _refresh_current_status(conn, app_id)


def add_do_not_track(conn: sqlite3.Connection, company: str, role: str) -> None:
    conn.execute("INSERT OR IGNORE INTO do_not_track(company, role) VALUES(?,?)", (company, role))


def is_do_not_track(conn: sqlite3.Connection, company: str, role: str) -> bool:
    return any(_norm(c) == _norm(company) and _norm(r) == _norm(role) for c, r in do_not_track_list(conn))
