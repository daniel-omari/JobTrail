"""Shared fixtures. The egress guard is applied to the WHOLE test session: any attempt to open a
network connection to anything other than this machine fails the test run."""
from __future__ import annotations

import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobtrail.config import Config
from jobtrail.db import connect
from jobtrail.main import create_app
from jobtrail.sources.synthetic import SyntheticInbox

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "inbox.json"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


class EgressBlocked(AssertionError):
    pass


_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
egress_attempts: list[object] = []


def _check(sock, address):
    if sock.family == getattr(socket, "AF_UNIX", object()):
        return
    host = address[0] if isinstance(address, tuple) else address
    if host not in LOCAL_HOSTS:
        egress_attempts.append(address)
        raise EgressBlocked(f"Outbound connection attempted to {address!r}")


def _guarded_connect(self, address):
    _check(self, address)
    return _real_connect(self, address)


def _guarded_connect_ex(self, address):
    _check(self, address)
    return _real_connect_ex(self, address)


def pytest_configure(config):
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex


def pytest_unconfigure(config):
    socket.socket.connect = _real_connect
    socket.socket.connect_ex = _real_connect_ex


@pytest.fixture
def inbox() -> SyntheticInbox:
    return SyntheticInbox(FIXTURES)


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(data_dir=tmp_path / "data")


@pytest.fixture
def make_client(config, inbox):
    def _make(source=None):
        app = create_app(config, source_factory=lambda: source or inbox)
        return TestClient(app)
    return _make


@pytest.fixture
def client(make_client):
    with make_client() as c:
        yield c


@pytest.fixture
def conn(config):
    from jobtrail.db import init_db
    init_db(config.db_path)
    c = connect(config.db_path)
    yield c
    c.close()


def all_canaries(inbox: SyntheticInbox) -> list[str]:
    return [m["canary"] for m in inbox.meta().values() if m.get("canary")]
