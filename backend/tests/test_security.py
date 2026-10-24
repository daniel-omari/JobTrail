"""The local API refuses requests that other websites in the same browser could forge."""
from fastapi.testclient import TestClient

from jobtrail.main import create_app


def _bare_client(config, inbox, **headers):
    return TestClient(create_app(config, source_factory=lambda: inbox, llm_factory=lambda m: None), headers=headers)


def test_dns_rebinding_host_is_refused(config, inbox):
    with _bare_client(config, inbox) as c:
        r = c.get("/api/everything", headers={"host": "evil.example:8000"})
    assert r.status_code == 403 and r.json()["detail"] == "Unexpected Host header"


def test_our_own_hosts_are_answered(config, inbox):
    with _bare_client(config, inbox) as c:
        for host in ("127.0.0.1:8000", "localhost:8000"):
            assert c.get("/api/status", headers={"host": host}).status_code == 200


def test_forged_post_without_header_is_refused(config, inbox):
    """What a hidden form on a malicious page could send."""
    with _bare_client(config, inbox) as c:
        c.post("/api/scan", headers={"x-jobtrail": "1"})
        r = c.post("/api/delete-all?confirm=true")
        assert r.status_code == 403 and r.json()["detail"] == "Missing X-JobTrail header"
        assert c.get("/api/applications").json() != []  # nothing was deleted


def test_cross_site_origin_is_refused_even_with_header(config, inbox):
    with _bare_client(config, inbox) as c:
        r = c.post("/api/scan", headers={"x-jobtrail": "1", "origin": "https://evil.example"})
        assert r.status_code == 403 and r.json()["detail"] == "Cross-site request refused"
        ok = c.post("/api/scan", headers={"x-jobtrail": "1", "origin": "http://testserver"})
        assert ok.status_code == 200


def test_no_cors_permission_is_ever_granted(config, inbox):
    with _bare_client(config, inbox) as c:
        r = c.options("/api/delete-all", headers={
            "origin": "https://evil.example", "access-control-request-method": "POST",
            "access-control-request-headers": "x-jobtrail"})
    assert "access-control-allow-origin" not in r.headers


def test_reads_work_without_the_header(config, inbox):
    with _bare_client(config, inbox) as c:
        assert c.get("/api/overview").status_code == 200
