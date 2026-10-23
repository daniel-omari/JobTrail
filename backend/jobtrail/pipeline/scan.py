"""Scan orchestrator: headers first, bodies only through the Gate, raw text never stored."""
from __future__ import annotations

import sqlite3
from collections import Counter

from .. import repo
from ..logging_setup import get_logger, message_hash, short_hash
from ..models import Extraction, ScanSummary
from ..sources.base import Body, Header, InboxSource
from . import rules
from .crosscheck import crosscheck
from .detector import detect
from .extract_llm import LlmError, OllamaExtractor
from .extract_rules import extract_fields, to_extraction
from .gate import Gate
from .html_text import raw_text, split_text
from .rules import status_evidence


def stored_summary(ex: Extraction) -> str:
    return f"company={ex.company}; role={ex.role}; status={ex.status.value}"


def _context(conn: sqlite3.Connection, settings: dict) -> rules.RuleContext:
    trusted, rejected = repo.sender_lists(conn)
    return rules.RuleContext(
        excluded_labels=set(settings.get("excluded_labels") or []),
        trusted=trusted,
        rejected=rejected,
        do_not_track=repo.do_not_track_list(conn),
    )


def _quarantine(conn, header: Header, ledger_id: int, flags: list[dict], prefill: dict, summary: ScanSummary) -> str:
    repo.quarantine_add(conn, header.id, header.sender, header.subject, header.date, flags, prefill, ledger_id)
    repo.ledger_set_stored(conn, ledger_id, "quarantined: nothing added to tracker (" + ", ".join(f["code"] for f in flags) + ")")
    summary.quarantined += 1
    return "quarantined"


def _store(conn, header: Header, ex: Extraction, ledger_id: int, summary: ScanSummary) -> str:
    source = rules.platform_for(header) or header.domain
    repo.record_event(conn, ex, header.date, source, rules.how_applied(source), message_hash(header.id))
    repo.ledger_set_stored(conn, ledger_id, stored_summary(ex))
    summary.tracked += 1
    return "tracked"


def process_opened(
    conn: sqlite3.Connection, header: Header, body: Body, ledger_id: int, summary: ScanSummary,
    llm: OllamaExtractor | None = None, defences: bool = True,
) -> str:
    """Extract and store fields for one opened email. Returns the outcome. The body goes out of scope here."""
    visible, _hidden = split_text(body)
    prefill = extract_fields(visible, header)  # rules-only answer: fallback, and the pre-fill if quarantined

    if not defences:
        # DEMO ONLY: what an undefended integration does. Raw body (hidden text included) straight into a
        # naive prompt, no detector, no cross-check; whatever the model says is stored.
        try:
            ex = llm.extract_naive(raw_text(body), header) if llm else to_extraction(extract_fields(raw_text(body), header))
        except LlmError:
            ex = None
        if ex is None:
            repo.ledger_set_stored(conn, ledger_id, "nothing stored (details could not be read)")
            return "unreadable"
        return _store(conn, header, ex, ledger_id, summary)

    # Layer 1: injection detector, before any AI sees the email.
    flags = detect(body)
    if flags:
        return _quarantine(conn, header, ledger_id, flags, prefill, summary)

    if llm is None:
        ex = to_extraction(prefill)
        if ex is None:
            repo.ledger_set_stored(conn, ledger_id, "nothing stored (details could not be read)")
            return "unreadable"
        return _store(conn, header, ex, ledger_id, summary)

    # Layer 2: strict-format extraction from VISIBLE text only, with a hardened prompt.
    try:
        ex = llm.extract(visible, header)
    except LlmError as e:
        flag = {
            "code": "ai_invalid_output",
            "reason": "AI output failed validation",
            "excerpt": "",
            "info": "The local AI's answer didn't match the strict format (three fields, fixed status list), "
                    f"so it was not trusted. Detail: {e}",
        }
        return _quarantine(conn, header, ledger_id, [flag], prefill, summary)

    # Layer 3: cross-check the AI against the rules' independent reading of the email.
    flags = crosscheck(ex, status_evidence(visible, header.subject), header, visible)
    if flags:
        return _quarantine(conn, header, ledger_id, flags, prefill, summary)
    return _store(conn, header, ex, ledger_id, summary)


def open_and_process(
    conn: sqlite3.Connection, gate: Gate, header: Header, rule: str, summary: ScanSummary,
    llm: OllamaExtractor | None,
) -> str:
    """Open one email through the Gate (ledger first), process it, and record that it was seen."""
    ledger_id, body = gate.open(header, rule)
    summary.opened += 1
    outcome = process_opened(conn, header, body, ledger_id, summary, llm, defences=summary.defences)
    del body
    repo.mark_seen(conn, message_hash(header.id), "quarantined" if outcome == "quarantined" else "opened")
    get_logger().info("scan.%s msg=%s", outcome, short_hash(header.id))
    conn.commit()
    return outcome


def run_scan(conn: sqlite3.Connection, source: InboxSource, llm: OllamaExtractor | None = None) -> ScanSummary:
    log = get_logger()
    settings = repo.get_settings(conn)
    ctx = _context(conn, settings)
    summary = ScanSummary(mode="llm" if llm else "rules", defences=bool(settings["defences"]))
    skipped = Counter()
    gate = Gate(source, conn)

    for header in source.list_headers():
        summary.checked += 1
        h = message_hash(header.id)
        if repo.seen_outcome(conn, h):
            summary.already_seen += 1
            continue
        decision = rules.classify(header, ctx)
        if decision.action == "skip":
            summary.skipped += 1
            skipped[decision.reason] += 1
            continue
        if decision.action == "review":
            repo.review_add(conn, header.id, header.sender, header.subject, header.date)
            repo.mark_seen(conn, h, "review")
            summary.review += 1
            log.info("scan.review msg=%s", short_hash(header.id))
            continue
        open_and_process(conn, gate, header, decision.reason, summary, llm)

    summary.skipped_by_reason = dict(skipped)
    repo.scan_run_add(conn, summary)
    conn.commit()
    log.info("scan.done checked=%s opened=%s skipped=%s review=%s quarantined=%s",
             summary.checked, summary.opened, summary.skipped, summary.review, summary.quarantined)
    return summary
