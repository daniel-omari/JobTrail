"""Canary tests: secrets planted in personal emails must never reach storage, logs or API output."""
import glob

from tests.conftest import all_canaries


def _db_and_log_bytes(config) -> bytes:
    data = b""
    for path in glob.glob(str(config.db_path) + "*") + [str(config.log_path)]:
        with open(path, "rb") as f:
            data += f.read()
    return data


def test_canaries_never_stored_logged_or_returned(client, config, inbox):
    summary = client.post("/api/scan").json()
    assert summary["opened"] > 0
    api_text = client.get("/api/applications").text + client.get("/api/ledger").text + \
        client.get("/api/applications?archived=true").text
    stored = _db_and_log_bytes(config)
    canaries = all_canaries(inbox)
    assert len(canaries) >= 10
    for canary in canaries:
        assert canary.encode() not in stored, f"{canary} found in database/log"
        assert canary not in api_text, f"{canary} returned by the API"


def test_no_raw_body_text_is_stored(client, config, inbox):
    client.post("/api/scan")
    stored = _db_and_log_bytes(config)
    # A distinctive sentence from an opened hiring email must not be persisted anywhere.
    assert b"our talent team will review it carefully" not in stored


def test_canaries_never_sent_to_the_ai_model(make_client, config, inbox, stub_llm):
    with make_client(llm=stub_llm) as c:
        summary = c.post("/api/scan").json()
    assert summary["mode"] == "llm"
    assert len(stub_llm.requests) == summary["opened"]  # one request per opened email, nothing else
    sent = "\n".join(stub_llm.requests)
    for canary in all_canaries(inbox):
        assert canary not in sent, f"{canary} was sent to the model"
    stored = _db_and_log_bytes(config)
    for canary in all_canaries(inbox):
        assert canary.encode() not in stored
