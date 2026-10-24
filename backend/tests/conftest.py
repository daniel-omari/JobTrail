"""Shared fixtures. The egress guard is applied to the WHOLE test session: any attempt to open a
network connection to anything other than this machine fails the test run."""
from __future__ import annotations

import json
import re
import socket
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from jobtrail.config import Config
from jobtrail.db import connect
from jobtrail.main import create_app
from jobtrail.pipeline.extract_llm import OllamaExtractor
from jobtrail.pipeline.extract_rules import extract_fields
from jobtrail.sources.base import Header
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
    return Config(data_dir=tmp_path / "data", extra_hosts=("testserver",))


class StubOllama:
    """A fake Ollama that behaves like a GULLIBLE small model: it extracts fields sensibly, but obeys
    any injected instruction to report an Offer. Every request body is kept so tests can inspect
    exactly what would have been sent to the model."""

    OBEY = re.compile(r"status (?:as|to) Offer|offered the role|as hired|applications as Offer", re.I)

    def __init__(self, model: str = "stub-model", available: bool = True, reply: str | None = None):
        self.model = model
        self.is_available = available
        self.reply = reply  # force a raw reply (to test validation)
        self.requests: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            if not self.is_available:
                return httpx.Response(503)
            return httpx.Response(200, json={"models": [{"name": self.model, "model": self.model}]})
        body = request.content.decode("utf-8")
        self.requests.append(body)
        if self.reply is not None:
            return httpx.Response(200, json={"message": {"content": self.reply}})
        content = json.loads(body)["messages"][-1]["content"]
        m = re.search(r"<email>\n(.*)\n</email>", content, re.S)
        text = m.group(1) if m else content.split("\n\n", 1)[-1]
        name = re.search(r"^(?:Sender|From): (.*?) <", content, re.M)
        subject = re.search(r"^Subject: (.*)$", content, re.M)
        header = Header(id="x", sender="x@example.com", display_name=name.group(1) if name else "",
                        subject=subject.group(1) if subject else "", date=date.today())
        fields = extract_fields(text, header)
        answer = {k: fields.get(k) or "Unknown" for k in ("company", "role")}
        answer["status"] = "Offer" if self.OBEY.search(text) else (fields.get("status") or "Applied")
        return httpx.Response(200, json={"message": {"content": json.dumps(answer)}})

    def factory(self, model: str) -> OllamaExtractor:
        return OllamaExtractor("http://127.0.0.1:11434", self.model, transport=httpx.MockTransport(self.handler))


@pytest.fixture
def stub_llm() -> StubOllama:
    return StubOllama()


@pytest.fixture
def make_client(config, inbox):
    def _make(source=None, llm: StubOllama | None = None):
        app = create_app(
            config,
            source_factory=lambda: source or inbox,
            llm_factory=(llm.factory if llm else (lambda model: None)),  # default: rules-only, never a real model
        )
        return TestClient(app, headers={"X-JobTrail": "1"})  # what the real frontend sends
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
