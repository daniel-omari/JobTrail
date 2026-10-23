"""Review queue: unknown-sender emails are shown by header only, and their bodies are read only on approval."""
from tests.conftest import all_canaries


def _item(c, subject_part):
    return next(r for r in c.get("/api/review").json() if subject_part in r["subject"])


def test_review_items_are_listed_but_never_opened(make_client, inbox, stub_llm):
    with make_client(llm=stub_llm) as c:
        c.post("/api/scan")
        items = c.get("/api/review").json()
        ledger = c.get("/api/ledger").json()["entries"]
    review_ids = {i for i, m in inbox.meta().items() if m["decision"] == "review"}
    assert len(items) == len(review_ids) == 3
    assert set(items[0]) == {"id", "sender", "subject", "received_date"}  # headers only
    assert review_ids.isdisjoint(inbox.body_reads)
    assert {e["subject"] for e in ledger}.isdisjoint({i["subject"] for i in items})


def test_approve_reads_body_once_tracks_it_and_trusts_the_sender(make_client, inbox, stub_llm):
    with make_client(llm=stub_llm) as c:
        c.post("/api/scan")
        item = _item(c, "Quayside")
        reads_before = len(inbox.body_reads)
        assert c.post(f"/api/review/{item['id']}/approve").json()["outcome"] == "tracked"
        apps = {(a["company"], a["current_status"]) for a in c.get("/api/applications").json()}
        ledger = c.get("/api/ledger").json()["entries"]
        rescan = c.post("/api/scan").json()
    assert len(inbox.body_reads) == reads_before + 1 and inbox.body_reads[-1] == "h15"
    assert ("Quayside Logistics", "Interview") in apps
    assert ledger[0]["rule"] == "approved_by_you" and "Quayside" in ledger[0]["stored_summary"]
    assert rescan["opened"] == 0 and rescan["review"] == 0


def test_reject_never_opens_and_is_not_requeued(make_client, inbox, config, stub_llm):
    with make_client(llm=stub_llm) as c:
        c.post("/api/scan")
        item = _item(c, "interview chat")  # the private email with a hiring-like subject
        assert c.post(f"/api/review/{item['id']}/reject").json()["outcome"] == "rejected"
        rescan = c.post("/api/scan").json()
        remaining = c.get("/api/review").json()
    assert "p10" not in inbox.body_reads
    assert rescan["review"] == 0 and all("interview chat" not in r["subject"] for r in remaining)
    stored = b"".join(open(p, "rb").read() for p in [config.db_path, config.log_path])
    for canary in all_canaries(inbox):
        assert canary.encode() not in stored
