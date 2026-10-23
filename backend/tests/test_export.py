"""Weekly UC journal export."""
import csv
import io
from datetime import date, timedelta

from tests.conftest import all_canaries


def test_default_is_last_7_days_and_includes_rejections_after_a_normal_clear(client, inbox):
    client.post("/api/scan")
    client.post("/api/archive/clear")  # normal clear keeps the last 7 days
    out = client.get("/api/export").json()
    assert out["start"] == str(date.today() - timedelta(days=6)) and out["end"] == str(date.today())
    assert "Copperleaf Systems" in out["text"] and "Application unsuccessful" in out["text"]
    assert "Kestrel Finance" in out["text"] and "Role closed or filled" in out["text"]
    expected = sum(1 for h in inbox.list_headers() if inbox.meta()[h.id]["kind"] == "hiring"
                   and inbox.meta()[h.id]["decision"] == "open" and h.date >= date.today() - timedelta(days=6))
    assert out["count"] == expected


def test_quarantined_attack_never_appears_in_the_export(client):
    client.post("/api/scan")
    wexford = [line for line in client.get("/api/export").json()["text"].splitlines() if "Wexford" in line]
    assert wexford == []  # its only email this week was the quarantined attack


def test_csv_has_the_journal_columns_and_no_secrets(client, inbox):
    client.post("/api/scan")
    r = client.get(f"/api/export?format=csv&start={date.today() - timedelta(days=40)}")
    assert r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    reader = csv.DictReader(io.StringIO(r.text))
    assert reader.fieldnames == ["Date", "Employer", "Role", "How applied", "Activity", "Outcome"]
    assert len(list(reader)) > 10
    for canary in all_canaries(inbox):
        assert canary not in r.text


def test_csv_neutralises_formula_injection(client):
    client.post("/api/applications", json={"company": "=HYPERLINK(\"http://x\")", "role": "Dev"})
    r = client.get("/api/export?format=csv")
    assert "'=HYPERLINK" in r.text


def test_empty_period(client):
    out = client.get("/api/export").json()
    assert out["count"] == 0 and "No job-search activity" in out["text"]
