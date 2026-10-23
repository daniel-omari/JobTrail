"""Synthetic inbox: fictional emails in fixtures/inbox.json.
Dates are stored as `days_ago` so the This week / This month views stay meaningful on any day."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .base import Body, Header, InboxSource


class SyntheticInbox(InboxSource):
    name = "synthetic"

    def __init__(self, path: Path, today: date | None = None):
        self._emails = {e["id"]: e for e in json.loads(Path(path).read_text(encoding="utf-8"))}
        self._today = today or date.today()
        self.body_reads: list[str] = []  # test hook: every body ever handed out

    def list_headers(self) -> list[Header]:
        return [
            Header(
                id=e["id"],
                sender=e["from"].lower(),
                display_name=e.get("from_name", ""),
                subject=e["subject"],
                date=self._today - timedelta(days=int(e["days_ago"])),
                labels=tuple(e.get("labels", [])),
            )
            for e in self._emails.values()
        ]

    def _read_body(self, message_id: str) -> Body:
        e = self._emails[message_id]
        self.body_reads.append(message_id)
        return Body(html=e.get("body_html"), text=e.get("body_text"))

    # Only for tests and the benchmark script: the app never reads `_meta`.
    def meta(self) -> dict[str, dict]:
        return {i: e.get("_meta", {}) for i, e in self._emails.items()}
