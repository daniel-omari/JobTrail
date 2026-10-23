"""Archive tools, manual editing, don't-track, and ledger redaction."""
from datetime import date, timedelta

from jobtrail import repo
from jobtrail.pipeline.scan import run_scan


def _by_company(c, archived):
    return {a["company"]: a for a in c.get(f"/api/applications?archived={str(archived).lower()}").json()}


def test_clear_keeps_the_last_7_days_and_redacts_ledger(client):
    client.post("/api/scan")
    archived = _by_company(client, True)
    old = {n for n, a in archived.items() if date.fromisoformat(a["last_update"]) < date.today() - timedelta(days=7)}
    recent = set(archived) - old
    assert old and recent  # fixtures include both
    assert client.post("/api/archive/clear").json()["removed"] == len(old)
    assert set(_by_company(client, True)) == recent
    ledger = client.get("/api/ledger").json()["entries"]
    redacted = [e for e in ledger if e["redacted"]]
    assert redacted and all(e["sender"] is None and e["subject"] is None for e in redacted)
    assert all(e["rule"] and e["opened_at"] for e in redacted)  # audit trail kept
    assert not any(name in (e["stored_summary"] or "") for e in ledger for name in old)
    # Cleared records don't come back on the next scan.
    client.post("/api/scan")
    assert set(_by_company(client, True)) == recent


def test_clear_refuses_less_than_7_days(client):
    assert client.post("/api/archive/clear?older_than=3").status_code == 422


def test_force_clean_needs_confirmation(client):
    client.post("/api/scan")
    assert client.post("/api/archive/force-clean").status_code == 400
    assert client.post("/api/archive/force-clean?confirm=true").json()["removed"] > 0
    assert _by_company(client, True) == {}


def test_manual_add_edit_stage_and_delete(client):
    a = client.post("/api/applications", json={"company": "Acme Ltd", "role": "Tester", "date": str(date.today())}).json()
    assert a["manual"] and a["current_status"] == "Applied"
    a = client.patch(f"/api/applications/{a['id']}", json={"status": "Interview", "role": "QA Tester"}).json()
    assert a["current_status"] == "Interview" and a["role"] == "QA Tester" and len(a["history"]) == 2
    assert client.get("/api/overview?range=week").json()["proceeding_now"] == 1
    assert client.delete(f"/api/applications/{a['id']}").json() == {"ok": True}
    assert client.get("/api/applications").json() == []


def test_restore_moves_a_misfiled_rejection_back(client):
    client.post("/api/scan")
    copperleaf = _by_company(client, True)["Copperleaf Systems"]
    restored = client.post(f"/api/applications/{copperleaf['id']}/restore").json()
    assert restored["archived"] is False and restored["current_status"] == "Applied"
    assert "Copperleaf Systems" in _by_company(client, False)


def test_do_not_track_removes_and_skips_future_emails(conn, inbox):
    repo.add_do_not_track(conn, "Brightlane Health", "Graduate Software Developer")
    conn.commit()
    summary = run_scan(conn, inbox)
    assert summary.skipped_by_reason.get("do_not_track") == 2
    assert all(a["company"] != "Brightlane Health" for a in repo.list_applications(conn))
    assert {"h03", "h04"}.isdisjoint(inbox.body_reads)


def test_do_not_track_via_api(client):
    client.post("/api/scan")
    halden = _by_company(client, False)["Halden Robotics"]
    assert client.post(f"/api/applications/{halden['id']}/do-not-track").json() == {"ok": True}
    assert "Halden Robotics" not in _by_company(client, False)
