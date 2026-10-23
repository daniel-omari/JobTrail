"""Cross-check the AI's answer against independent evidence the rules found in the visible text.
Catches an injection the detector missed: if the email's own words say 'unfortunately' but the
model says Offer, the model was probably manipulated (or simply wrong), so neither is trusted."""
from __future__ import annotations

from ..models import Extraction, Status
from ..sources.base import Header


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def crosscheck(ex: Extraction, evidence: Status | None, header: Header, visible_text: str) -> list[dict]:
    flags = []
    if evidence is not None and ex.status != evidence:
        flags.append({
            "code": "ai_rules_disagree",
            "reason": "AI output disagrees with rule evidence",
            "excerpt": f"AI said {ex.status.value}; the email's own wording indicates {evidence.value}.",
            "info": "The local AI's answer didn't match what the email actually says. That can mean hidden "
                    "instructions manipulated the AI, or the AI simply made a mistake. Either way it wasn't trusted. "
                    "If you release it, the form is pre-filled from the rules, not from the AI.",
        })
    haystack = _norm(f"{header.display_name} {header.sender} {header.subject} {visible_text}")
    if _norm(ex.company) not in haystack:
        flags.append({
            "code": "ai_company_not_in_email",
            "reason": "AI named a company that isn't in the email",
            "excerpt": f"AI said company = {ex.company!r}",
            "info": "The company the AI returned doesn't appear anywhere in the email, so the answer wasn't trusted.",
        })
    return flags
