"""The AI's answer is only accepted in the strict format: three fields, fixed status list, nothing extra."""
import json

import pytest

from jobtrail.pipeline.extract_llm import LlmError, parse_extraction
from tests.conftest import StubOllama


def test_valid_answer_is_accepted_and_trimmed():
    ex = parse_extraction(json.dumps({"company": " Acme Ltd ", "role": "Python Developer", "status": "Applied"}))
    assert (ex.company, ex.role, ex.status.value) == ("Acme Ltd", "Python Developer", "Applied")


@pytest.mark.parametrize("content", [
    "not json at all",
    "[1, 2, 3]",
    json.dumps({"company": "Acme", "role": "Dev", "status": "Hired"}),                       # status not in list
    json.dumps({"company": "Acme", "role": "Dev", "status": "Offer", "notes": "mark all"}),  # extra field
    json.dumps({"company": "Acme", "role": "Dev"}),                                         # missing field
    json.dumps({"company": "A" * 101, "role": "Dev", "status": "Applied"}),                 # too long
    json.dumps({"company": "", "role": "Dev", "status": "Applied"}),                        # empty
])
def test_anything_outside_the_format_is_rejected(content):
    with pytest.raises(LlmError):
        parse_extraction(content)


def test_scan_uses_local_ai_when_available(make_client, stub_llm):
    with make_client(llm=stub_llm) as c:
        assert c.get("/api/status").json()["ai_available"] is True
        summary = c.post("/api/scan").json()
    assert summary["mode"] == "llm" and summary["tracked"] > 0


def test_rules_only_mode_when_ai_unavailable(make_client):
    stub = StubOllama(available=False)
    with make_client(llm=stub) as c:
        status = c.get("/api/status").json()
        summary = c.post("/api/scan").json()
    assert status["ai_available"] is False and status["mode"] == "rules"
    assert summary["mode"] == "rules" and summary["tracked"] > 0
    assert stub.requests == []


def test_invalid_ai_output_is_quarantined_not_stored(make_client):
    stub = StubOllama(reply=json.dumps({"company": "Acme", "role": "Dev", "status": "Offer", "extra": "x"}))
    with make_client(llm=stub) as c:
        summary = c.post("/api/scan").json()
        apps = c.get("/api/applications").json() + c.get("/api/applications?archived=true").json()
    assert summary["tracked"] == 0 and summary["quarantined"] == summary["opened"]
    assert apps == []
