"""Weekly job-search summary for the UK Universal Credit journal: date, employer, role, how applied, outcome.
Built from dated events, so normal archive clearing (which keeps the last 7 days) never affects the current week."""
from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, timedelta

ACTIVITY = {
    "Applied": "Applied",
    "Assessment": "Invited to an assessment",
    "Interview": "Invited to interview",
    "Offer": "Job offer received",
    "Rejected": "Application unsuccessful",
    "Closed": "Role closed or filled",
}
OUTCOME = {
    "Applied": "Awaiting reply",
    "Assessment": "Progressed to assessment",
    "Interview": "Progressed to interview",
    "Offer": "Offer",
    "Rejected": "Unsuccessful",
    "Closed": "Vacancy closed",
}
COLUMNS = ["Date", "Employer", "Role", "How applied", "Activity", "Outcome"]


def default_range(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return today - timedelta(days=6), today


def rows(conn: sqlite3.Connection, start: date, end: date) -> list[dict]:
    q = conn.execute(
        "SELECT e.event_date, e.status, a.company, a.role, a.how_applied FROM events e "
        "JOIN applications a ON a.id = e.application_id WHERE e.event_date BETWEEN ? AND ? "
        "ORDER BY e.event_date, a.company", (start.isoformat(), end.isoformat()))
    return [
        {"Date": r["event_date"], "Employer": r["company"], "Role": r["role"], "How applied": r["how_applied"],
         "Activity": ACTIVITY[r["status"]], "Outcome": OUTCOME[r["status"]]}
        for r in q
    ]


def _d(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")


def summary_text(conn: sqlite3.Connection, start: date, end: date) -> str:
    items = rows(conn, start, end)
    head = f"Job search activity, {_d(start.isoformat())} to {_d(end.isoformat())}"
    if not items:
        return head + "\n\nNo job-search activity recorded in this period."
    applied = sum(r["Activity"] == "Applied" for r in items)
    progressed = sum(r["Outcome"].startswith("Progressed") or r["Outcome"] == "Offer" for r in items)
    unsuccessful = sum(r["Outcome"] in {"Unsuccessful", "Vacancy closed"} for r in items)
    lines = [head, f"{applied} application(s) made, {progressed} progressed, {unsuccessful} unsuccessful or closed.", ""]
    for r in items:
        lines.append(f"{_d(r['Date'])} - {r['Employer']} - {r['Role']} - {r['How applied']} - "
                     f"{r['Activity']} (outcome: {r['Outcome'].lower()})")
    return "\n".join(lines)


def csv_text(conn: sqlite3.Connection, start: date, end: date) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows(conn, start, end):
        # Neutralise spreadsheet formula injection from email-derived text.
        w.writerow({k: ("'" + v if isinstance(v, str) and v[:1] in "=+-@" else v) for k, v in r.items()})
    return buf.getvalue()
