"""Rules-only extraction. Used when the local AI is unavailable, and to pre-fill Quarantine
releases (so a released email never inherits a possibly-poisoned AI answer)."""
from __future__ import annotations

import re

from ..models import Extraction, Status
from ..sources.base import Header
from .rules import KNOWN_PLATFORMS, status_evidence

_NAME = r"[A-Z][\w&'-]*(?: [A-Z(][\w&'()-]*){0,3}"
_COMPANY_PATTERNS = [
    re.compile(rf"(?:position|role|vacancy|job) (?:at|with) ({_NAME})"),
    re.compile(rf"application (?:was )?sent to ({_NAME})"),
    re.compile(rf"(?:applying|applied|application) (?:to|at|with) ({_NAME})"),
    re.compile(rf"(?:^|\n)({_NAME}) has invited you"),
    re.compile(rf"on behalf of ({_NAME})"),
]
_ROLE_PATTERNS = [
    re.compile(r"for the ([A-Z][\w()/+&'-]*(?: [\w()/+&'-]+){0,6}?) (?:position|role|vacancy)"),
    re.compile(r"\bthe ([A-Z][\w()/+&'-]*(?: [\w()/+&'-]+){0,6}?) (?:position|role|vacancy)"),
    re.compile(r"as (?:a|an) ([A-Z][\w()/+&'-]*(?: [\w()/+&'-]+){0,6}?) (?:at|with)"),
]
_DISPLAY_SUFFIX = re.compile(
    r"\s+(?:recruiting|recruitment|careers|talent(?: team| acquisition)?|hiring team|people team|notifications|jobs)$", re.I)
_PLATFORM_NAMES = {v.lower() for v in KNOWN_PLATFORMS.values()} | {"linkedin"}


def _company(text: str, header: Header) -> str | None:
    for pattern in _COMPANY_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    name = _DISPLAY_SUFFIX.sub("", header.display_name).strip()
    if name and name.lower() not in _PLATFORM_NAMES:
        return name
    return None


def _role(text: str, subject: str) -> str | None:
    for pattern in _ROLE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    parts = re.split(r"\s[–—-]\s|:\s", subject)
    if len(parts) > 1:
        tail = re.sub(r"\(.*?\)", "", parts[-1]).strip()
        if tail and len(tail) <= 80:
            return tail
    return None


def extract_fields(visible_text: str, header: Header) -> dict:
    """Best-effort fields; any may be None."""
    status = status_evidence(visible_text, header.subject)
    return {
        "company": _company(visible_text, header),
        "role": _role(visible_text, header.subject),
        "status": status.value if status else None,
    }


def to_extraction(fields: dict) -> Extraction | None:
    if not all(fields.get(k) for k in ("company", "role", "status")):
        return None
    return Extraction(company=fields["company"][:100], role=fields["role"][:120], status=Status(fields["status"]))
