"""Notes are the user's own text: editable, shown in 'everything we hold', never put in the UC export."""


def test_notes_add_edit_and_show_in_everything(client):
    a = client.post("/api/applications", json={"company": "Acme Ltd", "role": "Dev", "notes": "Interview Thu 2pm"}).json()
    assert a["notes"] == "Interview Thu 2pm"
    a = client.patch(f"/api/applications/{a['id']}", json={"notes": "  Ask about hybrid  "}).json()
    assert a["notes"] == "Ask about hybrid"
    assert client.get("/api/everything").json()["applications"][0]["notes"] == "Ask about hybrid"
    assert "hybrid" not in client.get("/api/export").json()["text"]
    assert "hybrid" not in client.get("/api/export?format=csv").text


def test_notes_length_is_capped(client):
    a = client.post("/api/applications", json={"company": "Acme Ltd", "role": "Dev"}).json()
    assert client.patch(f"/api/applications/{a['id']}", json={"notes": "x" * 1001}).status_code == 422


def test_scanned_applications_start_with_empty_notes(client):
    client.post("/api/scan")
    assert all(a["notes"] == "" for a in client.get("/api/applications").json())
