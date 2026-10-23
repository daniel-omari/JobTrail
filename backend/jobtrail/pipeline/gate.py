"""The Gate: the only route from the pipeline to an email body.
It writes (and commits) an access-ledger row BEFORE asking the source for the body,
so every body ever read has a ledger entry. tests/test_gate.py checks bodies read == ledger rows."""
from __future__ import annotations

import sqlite3

from .. import repo
from ..logging_setup import get_logger, message_hash, short_hash
from ..sources.base import Body, Header, InboxSource


class Gate:
    def __init__(self, source: InboxSource, conn: sqlite3.Connection):
        self._source = source
        self._conn = conn

    def open(self, header: Header, rule: str) -> tuple[int, Body]:
        ledger_id = repo.ledger_insert(self._conn, message_hash(header.id), header.sender, header.subject, rule)
        get_logger().info("gate.open msg=%s rule=%s ledger=%s", short_hash(header.id), rule, ledger_id)
        return ledger_id, self._source._read_body(header.id)
