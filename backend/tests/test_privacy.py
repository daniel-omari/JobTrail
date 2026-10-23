"""'Everything we hold' is complete, and Delete all really removes data from the database file."""
import glob

from tests.conftest import all_canaries


def _file_bytes(config) -> bytes:
    return b"".join(open(p, "rb").read() for p in glob.glob(str(config.db_path) + "*"))


def test_everything_view_covers_all_stored_data(client, inbox):
    client.post("/api/scan")
    data = client.get("/api/everything").json()
    assert len(data["applications"]) > 0 and len(data["ledger"]) > 0
    assert len(data["review_queue"]) == 3 and len(data["quarantine"]) == 4
    assert data["processed_email_fingerprints"] > 0 and data["scan_runs"]
    text = client.get("/api/everything").text
    for canary in all_canaries(inbox):
        assert canary not in text


def test_delete_all_empties_the_view_and_the_file(client, config):
    client.post("/api/scan")
    assert b"Northwind Analytics" in _file_bytes(config)
    client.post("/api/delete-all?confirm=true")
    data = client.get("/api/everything").json()
    assert data["applications"] == [] and data["ledger"] == [] and data["review_queue"] == []
    assert data["quarantine"] == [] and data["processed_email_fingerprints"] == 0 and data["scan_runs"] == []
    stored = _file_bytes(config)
    for name in (b"Northwind Analytics", b"Halden Robotics", b"greenhouse-mail.io", b"offered the role"):
        assert name not in stored, name
