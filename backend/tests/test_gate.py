"""The Gate is the only path to a body, and it always writes the ledger first."""
from jobtrail import repo
from jobtrail.pipeline.scan import run_scan


def test_bodies_read_equals_ledger_rows(conn, inbox):
    run_scan(conn, inbox)
    assert len(inbox.body_reads) == repo.ledger_count(conn) > 0


def test_personal_noise_and_review_emails_are_never_opened(conn, inbox):
    run_scan(conn, inbox)
    meta = inbox.meta()
    for msg_id in inbox.body_reads:
        assert meta[msg_id]["decision"] == "open", msg_id
    never_opened = {i for i, m in meta.items() if m["decision"] in {"skip", "review"}}
    assert never_opened.isdisjoint(inbox.body_reads)


def test_rescan_opens_nothing_new(conn, inbox):
    first = run_scan(conn, inbox)
    reads = len(inbox.body_reads)
    second = run_scan(conn, inbox)
    assert second.opened == 0 and len(inbox.body_reads) == reads
    assert second.already_seen == first.opened + first.review


def test_ledger_records_why_and_what(conn, inbox):
    run_scan(conn, inbox)
    for entry in repo.ledger_list(conn):
        assert entry["rule"] in {"known_platform", "trusted_sender"}
        assert entry["stored_summary"] and entry["stored_summary"] != "pending"
