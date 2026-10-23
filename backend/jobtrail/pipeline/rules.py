"""Deterministic rules. These, not the AI, decide what is read.

classify() looks at HEADERS ONLY and returns one of:
  open   - known recruiting platform or a sender the user approved
  review - unknown sender, but the subject looks hiring-related (user decides; body stays unread)
  skip   - everything else, never opened
status_evidence() reads visible text for status keywords: used as the rules-only status and
as the independent evidence the AI's answer is cross-checked against."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import Status
from ..sources.base import Header

# Tier A: recruiting/ATS and assessment platforms (seeded from the brief).
KNOWN_PLATFORMS = {
    "myworkday.com": "Workday", "greenhouse-mail.io": "Greenhouse", "ashbyhq.com": "Ashby",
    "smartrecruiters.com": "SmartRecruiters", "teamtailor-mail.com": "Teamtailor", "workablemail.com": "Workable",
    "talent.icims.com": "iCIMS", "successfactors.eu": "SuccessFactors", "recruitee-inbox.com": "Recruitee",
    "beapplied-email.com": "Applied", "yello.co": "Yello", "deel.com": "Deel", "erecruiter.pl": "eRecruiter",
    "bamboohr.com": "BambooHR", "nofluffjobs.com": "No Fluff Jobs", "mail.amazon.jobs": "Amazon Jobs",
    "cappassessments.com": "Capp", "coderpad.io": "CoderPad", "hackerrank.com": "HackerRank", "codility.com": "Codility",
}
ASSESSMENT_PLATFORMS = {"cappassessments.com", "coderpad.io", "hackerrank.com", "codility.com"}
LINKEDIN_APPLICATIONS = "jobs-noreply@linkedin.com"
_LINKEDIN_APP_SUBJECT = re.compile(r"your application|application was (?:sent|viewed)", re.I)

# Job-alert noise: never opened, even though it mentions jobs.
NOISE_DOMAINS = {"match.indeed.com", "jobalert.indeed.com", "xing.com", "gradcracker.com"}
NOISE_ADDRESSES = {"updates-noreply@linkedin.com"}

HIRING_SUBJECT = re.compile(
    r"your application|application (?:received|confirmation|update)|thank(?:s| you) for applying|\binterview|"
    r"\bassessment\b|unfortunately|offer of employment|job offer|offer letter|next steps|coding test",
    re.I,
)
NON_JOB_CONTEXT = re.compile(r"\b(?:loan|mortgage|membership|visa|credit card|insurance|gym|council tax|tenancy)\b", re.I)


def _domain_match(domain: str, candidates) -> str | None:
    for d in candidates:
        if domain == d or domain.endswith("." + d):
            return d
    return None


def platform_for(header: Header) -> str | None:
    """Return the matched platform domain, or None."""
    if header.sender == LINKEDIN_APPLICATIONS:
        return "linkedin.com" if _LINKEDIN_APP_SUBJECT.search(header.subject) else None
    return _domain_match(header.domain, KNOWN_PLATFORMS)


def how_applied(source_domain: str) -> str:
    if source_domain == "linkedin.com":
        return "Online via LinkedIn"
    d = _domain_match(source_domain, KNOWN_PLATFORMS)
    if d in ASSESSMENT_PLATFORMS:
        return f"Online (assessment via {KNOWN_PLATFORMS[d]})"
    if d:
        return f"Online via {KNOWN_PLATFORMS[d]}"
    return "Email / recruiter"


@dataclass
class RuleContext:
    excluded_labels: set[str] = field(default_factory=set)
    trusted: set[str] = field(default_factory=set)
    rejected: set[str] = field(default_factory=set)
    do_not_track: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Decision:
    action: str  # open | review | skip
    reason: str


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def classify(header: Header, ctx: RuleContext) -> Decision:
    labels = {_norm(lbl) for lbl in header.labels}
    if labels & {_norm(lbl) for lbl in ctx.excluded_labels}:
        return Decision("skip", "excluded_label")
    if header.sender in NOISE_ADDRESSES or _domain_match(header.domain, NOISE_DOMAINS):
        return Decision("skip", "noise_sender")
    if header.sender in ctx.rejected:
        return Decision("skip", "rejected_sender")
    headline = _norm(f"{header.subject} {header.display_name}")
    for company, role in ctx.do_not_track:
        if _norm(company) in headline and _norm(role) in _norm(header.subject):
            return Decision("skip", "do_not_track")
    if platform_for(header):
        return Decision("open", "known_platform")
    if header.sender in ctx.trusted:
        return Decision("open", "trusted_sender")
    if HIRING_SUBJECT.search(header.subject) and not NON_JOB_CONTEXT.search(header.subject):
        return Decision("review", "hiring_signal_unknown_sender")
    return Decision("skip", "no_signal")


# Priority order matters: a rejection that opens with "Thank you for applying" is still a rejection.
_STATUS_PATTERNS: list[tuple[Status, re.Pattern]] = [
    (Status.REJECTED, re.compile(
        r"\bunfortunately\b|decided not to proceed|not (?:be )?(?:moving|move|proceed|progress)(?:ing)? forward|"
        r"\bunsuccessful\b|move forward with other candidates|regret to inform", re.I)),
    (Status.CLOSED, re.compile(
        r"has (?:now )?been filled|vacancy is (?:now )?closed|no longer accepting|position (?:is|has been) (?:closed|withdrawn)", re.I)),
    (Status.OFFER, re.compile(r"pleased to offer|offer of employment|formal offer|offer letter", re.I)),
    (Status.INTERVIEW, re.compile(
        r"invite you to (?:an? )?interview|interview invitation|like to invite you to (?:an? )?interview|schedule (?:an|your) interview", re.I)),
    (Status.ASSESSMENT, re.compile(r"online assessment|coding (?:test|assessment|challenge)", re.I)),
    (Status.APPLIED, re.compile(
        r"received your application|thank(?:s| you) for (?:applying|your application)|application (?:was )?sent|confirm that we have received", re.I)),
]


def status_evidence(visible_text: str, subject: str = "") -> Status | None:
    for status, pattern in _STATUS_PATTERNS:
        if pattern.search(visible_text):
            return status
    for status, pattern in _STATUS_PATTERNS:
        if pattern.search(subject):
            return status
    return None
