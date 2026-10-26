"""Prompt-injection detector. Runs BEFORE the local AI sees an email, so a flagged email never
reaches the model. Each flag carries a plain-English reason, a short excerpt of the flagged text,
and an Info tip explaining what the attack tried to do and why it was stopped."""
from __future__ import annotations

import re

from ..sources.base import Body
from .html_text import split_text

ZERO_WIDTH = re.compile("[​-‏‪-‮⁠-⁤﻿]")
BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{80,}={0,2}")

INSTRUCTION = re.compile(
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier|preceding)\b[^.\n]{0,20}(?:instructions?|text|rules)?"
    r"|ignore the rejection|disregard (?:all |any |the )?(?:previous|prior|above)"
    r"|\byou are now\b|(?:^|\n)\s*(?:system|assistant|developer)\s*:"
    r"|system (?:instruction|prompt|message|override)|(?:admin|administrator|developer|debug) mode"
    r"|note to the (?:ai|assistant|model)|(?:ai|language model|assistant) (?:processing|reading) this"
    r"|do not (?:tell|mention|inform|show)[^.\n]{0,30}user|as an ai\b",
    re.I,
)
MANIPULATION = re.compile(
    r"\b(?:mark|set|change|update|record|report|label)\b[^.\n]{0,60}\b(?:status|applications?|records?|candidate)\b"
    r"[^.\n]{0,40}\b(?:offer|hired|accepted|successful)\b"
    r"|\b(?:mark|set|change|update|modify|delete|remove|overwrite)\b[^.\n]{0,30}\b(?:all|every|other) (?:applications?|records?|entries)\b"
    r"|\bdelete (?:every|all|the)\b[^.\n]{0,30}\b(?:records?|applications?|rejected)\b",
    re.I,
)

INFO = {
    "zero_width": "Invisible zero-width characters were hidden inside the text, a common trick for sneaking "
                  "instructions past filters. The email was stopped before reaching the AI.",
    "hidden_instruction": "This email contains text styled to be invisible to you but readable by software. "
                          "It tries to instruct an AI that reads the email. Because it was caught first, the AI never saw it "
                          "and no records were changed.",
    "instruction_text": "The email contains text that tries to give instructions to software or an AI "
                        "(for example 'ignore previous instructions' or a fake 'SYSTEM:' message). Real recruiters don't write this. "
                        "The email was quarantined instead of being processed.",
    "record_manipulation": "The email tries to change the status of applications or affect other records. "
                           "JobTrail's AI can only fill in fields for the one email it reads, and this email was stopped before it got that far.",
    "encoded_blob": "A long encoded block was found, which can be used to smuggle hidden instructions. "
                    "The email was held for you to check.",
}
REASON = {
    "zero_width": "Hidden zero-width characters",
    "hidden_instruction": "Hidden text with instructions",
    "instruction_text": "Instruction-like text detected",
    "record_manipulation": "Attempt to change application records",
    "encoded_blob": "Suspicious encoded content",
}


def _excerpt(text: str, start: int, end: int, limit: int = 160) -> str:
    a, b = max(0, start - 50), min(len(text), end + 70)
    snippet = " ".join(text[a:b].split())
    if len(snippet) > limit:
        snippet = snippet[: limit - 1] + "…"
    return ("…" if a > 0 else "") + snippet


def _flag(code: str, excerpt: str) -> dict:
    return {"code": code, "reason": REASON[code], "excerpt": excerpt, "info": INFO[code]}


def detect(body: Body) -> list[dict]:
    visible, hidden = split_text(body)
    raw_visible = visible
    flags: list[dict] = []

    zw = ZERO_WIDTH.search(visible) or ZERO_WIDTH.search(hidden)
    if zw:
        src = visible if ZERO_WIDTH.search(visible) else hidden
        cleaned = ZERO_WIDTH.sub("", src)
        pos = len(ZERO_WIDTH.sub("", src[: zw.start()]))
        flags.append(_flag("zero_width", _excerpt(cleaned, pos, pos + 40)))
    visible = ZERO_WIDTH.sub("", visible)
    hidden = ZERO_WIDTH.sub("", hidden)

    if hidden:
        if INSTRUCTION.search(hidden) or MANIPULATION.search(hidden):
            # Show the start of the hidden message itself (it's attacker-written text, capped in length).
            flags.append(_flag("hidden_instruction", _excerpt(hidden, 0, 90)))

    m = INSTRUCTION.search(visible)
    if m:
        flags.append(_flag("instruction_text", _excerpt(visible, m.start(), m.end())))
    m = MANIPULATION.search(visible)
    if m:
        flags.append(_flag("record_manipulation", _excerpt(visible, m.start(), m.end())))

    m = BASE64_RUN.search(raw_visible) or BASE64_RUN.search(hidden)
    if m:
        flags.append(_flag("encoded_blob", m.group(0)[:40] + "…"))
    return flags
