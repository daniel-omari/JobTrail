---
doc: scope
status: approved
---

# JobTrail

A local-first job application tracker that reads only your hiring emails, logs every application automatically, and exports your weekly job search for the UC journal. It lets you verify what it touched and resists prompt injection hidden in emails.

## The Unique Kernel
**Privacy you can verify.** Other trackers ask you to trust them with your inbox. This one shows its work:
- headers are checked first, and bodies are opened only for likely hiring emails
- an access ledger records every email opened, why, and exactly what was stored
- canary tests prove that planted secrets in personal emails never reach storage, logs or the network.

The second layer: emails are treated as untrusted input to a local AI model, and the defence is shown working (attack with defences off vs on).

## Who It's For
A UK job seeker sending dozens of applications, often a Universal Credit claimant who must log job-search activity in the UC journal. Today they rebuild the week from memory or a half-kept spreadsheet. They'd like auto-tracking from email but (rightly) won't hand a small unknown app their whole inbox.

## The Core Loop
1. Scan the inbox. Hiring emails become tracker rows (company, role, status, date) and everything else is skipped unopened.
2. Glance at the tracker and the ledger.
3. Once a week, export a ready-to-paste UC journal summary.

They come back because every new confirmation, rejection or interview invite updates itself.

## Inspiration & Identity
Builds on the ideas (not the code) of his earlier LLM Blue-Team Guardrail project. Tone: calm, trustworthy, transparent, with the evidence shown rather than claimed. Wording should be honest ("designed to minimise data, verified by tests", never "secure").

## Why This Matters to the Learner
It solves his own problem as a job seeker logging activity for UC. It's also visible proof of his direction from backend development into AI security, and a project he wants to fully understand and explain in interviews.

## What "Working" Looks Like
In a 1–3 minute screen recording on a synthetic inbox (no real personal data):
1. Scan the inbox. Hiring emails appear in the tracker, and the ledger shows private emails were skipped **without being opened**.
2. Prove it with the "everything we hold about you" view, the canary tests passing, and nothing leaving the machine.
3. **The "oh, that's cool" beat:** a malicious recruiter email is run with defences off (the local model is fooled) and then on (flagged, quarantined, no records changed).
4. One-click weekly UC journal export.

## The POC Boundary
- Synthetic inbox fixtures: hiring, personal (with canaries), noise and malicious emails.
- **Rules decide what gets read:** a headers-first filter. Known recruiting platforms are processed, other emails with hiring signals go to a minimal review queue (sender + subject only), and everything else is never opened.
- **Local LLM via Ollama** extracts company / role / status into a strict JSON schema. It's validated, has no tools, and sees one email at a time.
- Model output is cross-checked against rule evidence. Inconsistent or injection-flagged emails are quarantined.
- Rules-only fallback when Ollama isn't running.
- Raw email bodies are never stored.
- Tracker, access ledger, "everything we hold" view, Delete all.
- Defences on/off toggle for the demo.
- Weekly UC journal export (text + CSV).
- Canary tests in CI, plus recall/privacy numbers in the README.
- Nothing leaves the machine: no server, accounts or telemetry.

## Later
- Real Gmail read-only adapter (OAuth testing mode). Sources are pluggable adapters, so it can be added later.
- One-click Gmail access revocation.
- A richer review queue (learned allowlist management, bulk approve).

## Explicitly Cut
- **Gmail import:** a restricted scope, it carries OAuth/verification overhead, and it isn't needed to prove the kernel on a synthetic inbox.
- **Cloud LLM:** it would break "nothing leaves the machine".
- **Multi-user, cloud hosting, mobile app:** contradict local-first and aren't needed for a solo demo.
- **Any email write access, auto-reply or sending:** outside the privacy model; read-only by design.
