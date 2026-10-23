"""The test session's egress guard really blocks outbound connections (so the other tests prove something)."""
import socket

import pytest

from tests.conftest import EgressBlocked


def test_outbound_connection_is_blocked():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(EgressBlocked):
            s.connect(("203.0.113.10", 80))  # TEST-NET-3 documentation address
    finally:
        s.close()


def test_full_scan_makes_no_outbound_connection(client):
    from tests import conftest
    before = len(conftest.egress_attempts)
    client.post("/api/scan")
    assert len(conftest.egress_attempts) == before


def test_security_headers_present(client):
    r = client.get("/api/status")
    assert "connect-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["referrer-policy"] == "no-referrer"
