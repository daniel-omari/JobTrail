"""The demo, as a test. The stub model is deliberately gullible (it obeys injected instructions),
like the real small models in scripts/model_probe.py.
  defences OFF -> the hidden-text rejection is stored as an Offer
  defences ON  -> it is quarantined, the AI never sees it, and every other record is unaffected"""
import pytest

from tests.conftest import StubOllama


def _all_apps(c):
    return {(a["company"], a["role"]): a["current_status"]
            for a in c.get("/api/applications").json() + c.get("/api/applications?archived=true").json()}


def _set_defences(c, on: bool):
    assert c.put("/api/settings", json={"defences": on}).json()["defences"] is on


def test_defences_off_lets_the_attack_through(make_client):
    stub = StubOllama()
    with make_client(llm=stub, demo=True) as c:
        _set_defences(c, False)
        summary = c.post("/api/scan").json()
        apps = _all_apps(c)
    assert summary["defences"] is False
    assert apps[("Wexford Media", "Junior Software Engineer")] == "Offer"  # the rejection became an Offer


def test_defences_on_quarantines_the_attack_and_changes_nothing_else(make_client, inbox):
    baseline_stub = StubOllama()
    stub = StubOllama()
    with make_client(llm=stub) as c:
        summary = c.post("/api/scan").json()
        apps = _all_apps(c)
        quarantined = c.get("/api/quarantine").json()

    assert summary["quarantined"] == 4
    assert {q["subject"] for q in quarantined} == {
        h.subject for h in inbox.list_headers() if inbox.meta()[h.id]["kind"] == "malicious"
    }
    wexford = next(q for q in quarantined if q["sender"].endswith("greenhouse-mail.io") and "Update" in q["subject"])
    assert any("offered the role" in r["excerpt"] for r in wexford["reasons"])
    assert wexford["rules_prefill"]["status"] == "Rejected"  # release would pre-fill the truth, not the attack

    # The AI never saw any malicious email.
    assert not any("offered the role" in r or "SYSTEM INSTRUCTION" in r for r in stub.requests)
    # Wexford stays at its genuine earlier status; nobody else became an Offer.
    assert apps[("Wexford Media", "Junior Software Engineer")] == "Applied"
    offers = [k for k, v in apps.items() if v == "Offer"]
    assert offers == [("Halden Robotics", "Software Engineer (Graduate)")]
    del baseline_stub


def test_release_uses_rules_prefill_and_discard_stores_nothing(make_client):
    with make_client(llm=StubOllama()) as c:
        c.post("/api/scan")
        items = c.get("/api/quarantine").json()
        wexford = next(q for q in items if "Update on your application" in q["subject"])
        r = c.post(f"/api/quarantine/{wexford['id']}/release", json=wexford["rules_prefill"])
        assert r.status_code == 200
        apps = _all_apps(c)
        assert apps[("Wexford Media", "Junior Software Engineer")] == "Rejected"
        other = next(q for q in c.get("/api/quarantine").json())
        before = len(_all_apps(c))
        assert c.post(f"/api/quarantine/{other['id']}/discard").status_code == 200
        assert len(_all_apps(c)) == before
        ledger = c.get("/api/ledger").json()["entries"]
        assert any(e["stored_summary"].startswith("released by you") for e in ledger)
        assert any("discarded" in e["stored_summary"] for e in ledger)


def test_cross_check_catches_a_lying_model_the_detector_missed(make_client):
    # A model that always says Offer, on emails with no injection text at all.
    stub = StubOllama(reply='{"company": "Copperleaf Systems", "role": "Python Developer", "status": "Offer"}')
    with make_client(llm=stub) as c:
        c.post("/api/scan")
        reasons = {r["code"] for q in c.get("/api/quarantine").json() for r in q["reasons"]}
    assert "ai_rules_disagree" in reasons


def test_delete_all_requires_confirmation_and_empties_everything(make_client):
    with make_client(llm=StubOllama()) as c:
        c.post("/api/scan")
        assert c.post("/api/delete-all").status_code == 400
        assert c.post("/api/delete-all?confirm=true").status_code == 200
        assert _all_apps(c) == {}
        assert c.get("/api/ledger").json()["entries"] == []
        assert c.get("/api/quarantine").json() == []


@pytest.mark.ollama
def test_real_model_demo(make_client, config):
    """Run with: pytest -m ollama  (needs Ollama running with the chosen model)."""
    from jobtrail.config import DEFAULT_MODEL, OLLAMA_URL
    from jobtrail.main import create_app
    from jobtrail.pipeline.extract_llm import OllamaExtractor
    from fastapi.testclient import TestClient

    import dataclasses
    app = create_app(dataclasses.replace(config, demo=True),
                     llm_factory=lambda m: OllamaExtractor(OLLAMA_URL, DEFAULT_MODEL, timeout=120))
    with TestClient(app, headers={"X-JobTrail": "1"}) as c:
        _set_defences(c, False)
        c.post("/api/scan")
        assert _all_apps(c)[("Wexford Media", "Junior Software Engineer")] == "Offer"
        c.post("/api/delete-all?confirm=true")
        _set_defences(c, True)
        c.post("/api/scan")
        assert _all_apps(c)[("Wexford Media", "Junior Software Engineer")] == "Applied"
        assert len(c.get("/api/quarantine").json()) >= 4


def test_tracker_history_names_the_source_email_and_quarantine_links_the_application(make_client):
    with make_client(llm=StubOllama()) as c:
        c.post("/api/scan")
        wexford_app = next(a for a in c.get("/api/applications").json() if a["company"] == "Wexford Media")
        q = next(q for q in c.get("/api/quarantine").json() if "Update on your application" in q["subject"])
    assert [h["subject"] for h in wexford_app["history"]] == ["Application received – Junior Software Engineer"]
    assert wexford_app["history"][0]["source"] == "email" and wexford_app["history"][0]["rule"] == "known_platform"
    assert q["affects"] == {"company": "Wexford Media", "role": "Junior Software Engineer", "current_status": "Applied"}


def test_defences_off_history_shows_which_email_made_the_offer(make_client):
    with make_client(llm=StubOllama(), demo=True) as c:
        c.put("/api/settings", json={"defences": False})
        c.post("/api/scan")
        wexford_app = next(a for a in c.get("/api/applications").json() if a["company"] == "Wexford Media")
    assert [(h["status"], h["subject"]) for h in wexford_app["history"]][-1] == \
        ("Offer", "Update on your application – Junior Software Engineer")
