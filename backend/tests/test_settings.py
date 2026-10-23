"""Settings: excluded labels, scan on startup, auto-clean."""
from datetime import date, timedelta

from jobtrail import repo
from jobtrail.db import connect
from jobtrail.startup import run_startup_tasks
from tests.conftest import StubOllama


def test_excluded_labels_skip_before_anything_else(client, inbox):
    assert client.put("/api/settings", json={"excluded_labels": [" Banking ", "Banking"]}).json()["excluded_labels"] == ["Banking"]
    summary = client.post("/api/scan").json()
    banking = [h.id for h in inbox.list_headers() if "Banking" in h.labels]
    assert summary["skipped_by_reason"]["excluded_label"] == len(banking) == 2
    assert set(banking).isdisjoint(inbox.body_reads)


def test_labels_endpoint_lists_inbox_labels(client):
    assert {"Inbox", "Banking", "Health"} <= set(client.get("/api/labels").json())


def test_auto_clean_bounds(client):
    assert client.put("/api/settings", json={"auto_clean_days": 3}).status_code == 422
    assert client.put("/api/settings", json={"auto_clean_never": True}).json()["auto_clean_days"] is None
    assert client.put("/api/settings", json={"auto_clean_days": 30}).json()["auto_clean_days"] == 30


def test_scan_on_startup_and_auto_clean(config, inbox):
    stub = StubOllama()
    first = run_startup_tasks(config, lambda: inbox, stub.factory)
    assert first == {"auto_cleaned": 0, "scanned": False}  # default: no startup scan
    conn = connect(config.db_path)
    repo.put_settings(conn, {"scan_on_startup": True, "auto_clean_days": 7})
    conn.close()
    second = run_startup_tasks(config, lambda: inbox, stub.factory)
    assert second["scanned"] and second["summary"]["mode"] == "llm" and second["summary"]["opened"] > 0
    third = run_startup_tasks(config, lambda: inbox, stub.factory)  # archive now has entries; old ones cleaned
    conn = connect(config.db_path)
    archived = repo.list_applications(conn, archived=True)
    conn.close()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    assert third["auto_cleaned"] >= 1 and all(a["last_update"] >= cutoff for a in archived)
