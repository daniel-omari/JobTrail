"""The inbox-source plug. Any email provider (the synthetic fixtures today, Gmail later)
implements this. Headers are public to the pipeline; bodies are not: only the Gate may call
`_read_body`, and the Gate always writes the ledger first."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Header:
    id: str
    sender: str           # email address, lower-case
    display_name: str
    subject: str
    date: date
    labels: tuple[str, ...] = field(default_factory=tuple)

    @property
    def domain(self) -> str:
        return self.sender.rsplit("@", 1)[-1]


@dataclass(frozen=True)
class Body:
    html: str | None
    text: str | None


class InboxSource(ABC):
    name: str = "inbox"

    @abstractmethod
    def list_headers(self) -> list[Header]:
        """Return headers only (sender, subject, date, labels). Must not read bodies."""

    @abstractmethod
    def _read_body(self, message_id: str) -> Body:
        """Fetch one body. Private: call only via pipeline.gate.Gate."""
