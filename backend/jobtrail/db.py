"""SQLite connection and schema. One local file; no server."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    source TEXT NOT NULL,              -- platform domain, or 'manual'
    how_applied TEXT NOT NULL,
    current_status TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0,
    manual INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    event_date TEXT NOT NULL,          -- ISO date the email/stage happened
    message_hash TEXT                  -- NULL for manual stage changes
);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY,
    opened_at TEXT NOT NULL,
    message_hash TEXT NOT NULL,
    sender TEXT,                       -- NULL once redacted
    subject TEXT,                      -- NULL once redacted
    rule TEXT NOT NULL,                -- why it was opened
    stored_summary TEXT,               -- exactly what was kept
    redacted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS seen_messages (
    message_hash TEXT PRIMARY KEY,
    outcome TEXT NOT NULL              -- opened | review | rejected_review | quarantined
);
CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    received_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quarantine (
    id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL UNIQUE,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    received_date TEXT NOT NULL,
    reasons TEXT NOT NULL,             -- JSON list of {code, reason, excerpt, info}
    rules_prefill TEXT NOT NULL,       -- JSON {company, role, status} from rules only
    ledger_id INTEGER
);
CREATE TABLE IF NOT EXISTS trusted_senders (address TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS rejected_senders (address TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS do_not_track (
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (company, role)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scan_runs (
    id INTEGER PRIMARY KEY,
    ran_at TEXT NOT NULL,
    checked INTEGER NOT NULL,
    opened INTEGER NOT NULL,
    skipped INTEGER NOT NULL,
    review INTEGER NOT NULL,
    quarantined INTEGER NOT NULL,
    mode TEXT NOT NULL,
    defences INTEGER NOT NULL
);
"""

ALL_TABLES = [
    "events", "applications", "ledger", "seen_messages", "review_queue", "quarantine",
    "trusted_senders", "rejected_senders", "do_not_track", "settings", "scan_runs",
]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA secure_delete = ON")  # overwrite deleted content instead of leaving it in free pages
    return conn


def init_db(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
