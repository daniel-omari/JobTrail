"""Shared types. `Extraction` is the strict shape any extractor (rules or AI) must return."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Status(str, Enum):
    APPLIED = "Applied"
    ASSESSMENT = "Assessment"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    CLOSED = "Closed"


PROCEEDING = {Status.ASSESSMENT, Status.INTERVIEW, Status.OFFER}
ENDED = {Status.REJECTED, Status.CLOSED}


class Extraction(BaseModel):
    """Exactly three fields. Anything else (extra keys, unknown status, huge strings) is rejected."""

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=120)
    status: Status


class ScanSummary(BaseModel):
    checked: int = 0
    opened: int = 0
    skipped: int = 0
    already_seen: int = 0
    review: int = 0
    quarantined: int = 0
    tracked: int = 0
    mode: str = "rules"
    defences: bool = True
    skipped_by_reason: dict[str, int] = Field(default_factory=dict)


class Application(BaseModel):
    id: int
    company: str
    role: str
    source: str
    how_applied: str
    current_status: Status
    archived: bool
    manual: bool
    applied_date: date | None = None
    last_update: date | None = None


class LedgerEntry(BaseModel):
    id: int
    opened_at: str
    sender: str | None
    subject: str | None
    rule: str
    stored_summary: str | None
    redacted: bool
