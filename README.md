# JobTrail

**A local-first job application tracker that reads only your hiring emails, logs every application automatically, and exports your weekly job search for the Universal Credit journal. It shows you exactly what it touched, and it resists prompt injection hidden in emails.**

> Built solo for [Build With AI: Basics](https://learn-ai-basics.devpost.com/) (Devpost Learn), using the Devpost Learn skill pack's plan-first workflow. The planning documents are in [`devpost/`](devpost/): [`scope.md`](devpost/scope.md), [`prd.md`](devpost/prd.md), [`spec.md`](devpost/spec.md) and the build [`checklist.md`](devpost/checklist.md).

## The problem

Job seekers send dozens of applications, and keeping track by hand is a chore that rarely gets kept up. In the UK, Universal Credit claimants also have to record their job-search activity in the UC journal, and many rebuild the week from memory.

Auto-tracking from email would solve this, but giving a small, unknown app access to your inbox is a real privacy risk. So the question JobTrail is built around is:

> *"Why should I trust this app not to read or keep my other emails?"*

JobTrail's answer: **don't take our word for it. Check.**

## What it does

- **Scan Now** checks email headers (sender, subject, date, labels) and opens **only** emails from recruiting platforms, or from senders you approve.
- **Tracker:** each application with its stage (*Still pending reply…*, *Stage: Interview!*, *Stage: Offer!*). There's search, a status history, your own private notes, manual add/edit/delete and "don't track this", plus a Rejected / No Response archive grouped by month.
- **Overview:** one half-circle gauge showing proceeding, awaiting reply and rejected, with This week / This month / All time.
- **Review:** emails from unknown senders that *look* job-related wait here, showing **sender, subject and date only**. They're opened only if you approve.
- **Quarantine:** emails that try to manipulate the app or its AI, with the reason, a short excerpt and a plain-English explanation.
- **Privacy:** an access ledger of every email opened, why, and exactly what was kept, plus "everything we hold about you" and Delete all.
- **Export:** a ready-to-paste weekly summary for the UC journal (date, employer, role, how applied, outcome), plus CSV.

## How it works

```
Browser (React) ──/api──▶ FastAPI on 127.0.0.1 ──▶ Scan
                                                    │ 1. headers only
                                                    ▼
                               Inbox source ◀── Gate: writes the access ledger FIRST, then returns the body
                                                    │ 2. only for known platforms / approved senders
                                                    ▼
             Injection detector ─▶ Local AI (Ollama, qwen2.5:7b) ─▶ Cross-check vs rules
                   │ flagged                 strict JSON, no tools             │ disagree
                   └──────────────▶ Quarantine ◀───────────────────────────────┘
                                                    │ 3. only company / role / status / date stored
                                                    ▼
                                         SQLite file on your computer
```

- **The rules decide what is read.** The AI never makes that decision. It only fills three fields for one email at a time, its answer must match a fixed JSON schema, and it has no tools.
- **The Gate** writes the ledger entry *before* returning an email body, and it is the only code that asks the inbox source for a body. That's by design and checked by a test (bodies read = ledger rows), not enforced by the language: Python can't stop another module calling a "private" method, so the test is what holds it.
- **Raw email text is never stored.** Skipped emails are only counted.
- **Protected local API.** "Only on 127.0.0.1" isn't enough on its own: any website open in your browser can send requests to `127.0.0.1`. JobTrail answers only its own `Host` names, which blocks DNS rebinding. It also requires a custom `X-JobTrail` header on every request that changes data, which blocks cross-site request forgery, because other sites can't add custom headers without a CORS permission JobTrail never grants.
- **One process, one origin.** FastAPI serves the built React app and binds to `127.0.0.1`. A `Content-Security-Policy` header (`connect-src 'self'`) makes the browser refuse to contact any other site. Fonts are bundled locally, there are no CDNs, and the API docs page is disabled because it loads from a CDN.

## Privacy claims and the evidence for each

JobTrail is **designed to minimise data, and that is verified by tests**. Every claim below has a test you can run (`pytest` in `backend/`), and CI runs them on every push.

| Claim | Evidence |
|---|---|
| Personal emails are never opened | `tests/test_gate.py`: every body read was from an allowed sender. The benchmark shows **0 / 10 personal emails opened**. |
| Every opened email is in the ledger, and it's logged first | `tests/test_gate.py`: bodies read == ledger rows |
| Planted secrets never reach storage, logs, the API or the AI | `tests/test_canaries.py`: 13 canary strings in personal emails are searched for in the database file, the log file, every API response and every request sent to the model |
| Nothing connects anywhere except this machine | `tests/test_egress.py`: the whole test session blocks any non-localhost connection and fails if one is attempted. The browser enforces the CSP. In DevTools → Network, everything is `127.0.0.1`. |
| Review items stay unopened until approved | `tests/test_review.py` |
| Other websites can't use the local API | `tests/test_security.py`: requests with a foreign `Host` (DNS rebinding), without the `X-JobTrail` header (cross-site request forgery), or with a foreign `Origin` are refused with 403, and no CORS permission is ever granted |
| Delete all really deletes | `tests/test_privacy.py`: after Delete all, the database file's bytes no longer contain the stored company names (`secure_delete` + `VACUUM`) |
| Clearing old records keeps an audit trail without personal details | `tests/test_cleanup.py`: ledger lines are redacted (date and reason kept; sender, subject and details removed) |

## The prompt-injection defence

Emails are untrusted input to an AI. The demo attack is a genuine-looking **rejection** with hidden text (`display:none`) telling "the AI assistant processing this email" that the candidate was offered the role.

- **Defences off** (a toggle that exists **only in demo mode**, `python -m jobtrail --demo`, with an amber banner): the raw email goes straight into a simple prompt. The real local model (qwen2.5:7b) logs the rejection as an **Offer**, and the Overview's green segment grows.
- **Defences on:** the detector catches the hidden instruction **before the AI sees it**. The email goes to Quarantine with its reason and excerpt, and no records change. "Release" pre-fills the entry from the rules (*Rejected*), never from the AI.

Three layers, because one wasn't enough:

1. **Visible text only, with hidden elements stripped**, and a **detector** for instruction-like text, hidden instructions, zero-width characters, attempts to change other records, and encoded blobs.
2. **Strict extraction:** a hardened prompt that treats the email as data, a JSON schema enforced by Ollama, and Pydantic validation (three fields, a fixed status list, no extra keys).
3. **Cross-check:** if the AI's status disagrees with what the email's own wording says, or it names a company that isn't in the email, the result isn't trusted.

**What we measured** (`scripts/model_probe.py`): the hardened prompt *alone* did not stop the hidden-text attack once the hidden text reached the model, and both models tested were fooled. A visible "SYSTEM INSTRUCTION" email fooled both models even with visible text only. That's why the detector runs *before* the model, and why the cross-check runs after it.

By design, even a fooled model can only mislabel the one email it is reading. It has no tools, no history and no access to other records, so "mark all applications as Offer" fails by architecture, not just by filtering.

## Benchmark

`python scripts/benchmark.py [--model qwen2.5:7b]` on the 40-email synthetic inbox (19 hiring, 10 personal with canaries, 7 job-alert/non-job "application" emails, 4 malicious):

| Measure | Rules only | Local AI (qwen2.5:7b) |
|---|---|---|
| Hiring emails caught (tracked or sent to Review) | 19 / 19 | 19 / 19 |
| Known-platform emails extracted fully correctly | 17 / 17 | 17 / 17 |
| Tricky unknown-sender hiring emails sent to Review (unopened) | 2 / 2 | 2 / 2 |
| Personal emails opened | 0 / 10 | 0 / 10 |
| Job-alert / non-job "application" emails opened | 0 / 7 | 0 / 7 |
| Canary secrets found in database or log | 0 / 13 | 0 / 13 |
| Prompt-injection emails quarantined | 4 / 4 | 4 / 4 |
| Genuine hiring emails wrongly quarantined | 0 / 19 | 0 / 19 |

**Read these honestly.** The inbox and the rules were written by the same person, so these numbers show the pipeline behaves as designed. They are **not** a measure of real-world accuracy. Real inboxes will have formats these rules haven't seen.

Model comparison (`scripts/model_probe.py`, RTX 5080): qwen2.5:7b got all three fields right on 17/17 emails at about 0.24s each. llama3.2:3b got 16/17 at about 0.14s. Both were fooled by the attack with defences off.

## Run it

Requirements: Python 3.12+ (developed on 3.14), Node 20+ (to build the frontend), and optionally [Ollama](https://ollama.com) with `qwen2.5:7b`. No accounts, API keys or `.env` file are needed.

```bash
# 1. Build the frontend (once)
cd frontend
npm ci
npm run build

# 2. Install the backend
cd ../backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"

# 3. Optional: the local AI
ollama pull qwen2.5:7b

# 4. Run it: opens http://127.0.0.1:8000
python -m jobtrail
```

Without Ollama, JobTrail runs in **rules-only mode** and shows a banner saying so. At startup it warms the model up in the background, so the first scan doesn't wait for the model to load.

**Demo mode:** `python -m jobtrail --demo` uses a separate data folder (`backend/data-demo`, wiped on each start), so your normal data is untouched. It also shows the demo-only controls: the defences on/off toggle and "Reset scan data". In normal mode those controls don't exist, and the API refuses to turn defences off.

**Tests:** `pytest` runs the whole suite with a deliberately gullible stub model, with no network or GPU needed. With Ollama running: `pytest -m ollama` runs the defence demo against the real model.

## Project layout

```
backend/jobtrail/
  sources/       inbox-source interface + the synthetic inbox (a Gmail source would plug in here)
  pipeline/      gate, rules, html_text, detector, extract_llm, extract_rules, crosscheck, scan
  api/           FastAPI routes
  repo.py        all SQL in one place
  cleanup.py     clear / force clean / delete all / ledger redaction
  export.py      UC journal summary + CSV
backend/fixtures/inbox.json   the synthetic inbox (fictional people and companies)
backend/tests/                the evidence
backend/scripts/              benchmark, model probe, fixture generator
frontend/src/                 React + TypeScript pages and components
devpost/                      scope, PRD, spec and build checklist (the plan this was built from)
```

## Limitations (honest)

- **Synthetic inbox only.** There is no real email connection yet. The `InboxSource` interface is shaped like Gmail's (labels, message IDs) so a read-only Gmail adapter can plug in. Gmail's `gmail.readonly` scope is a Google *restricted* scope, so a public release would need Google's verification and a security assessment.
- **Rules and fixtures are ours** (see the benchmark note). Unusual real-world formats will need more rules or will go to Review.
- **The detector is pattern-based.** A novel phrasing can get past it. The cross-check is a second net, not a guarantee.
- **No login.** Websites are blocked (see above), but another *program* running on the same computer could still call `127.0.0.1:8000` while JobTrail is open. It is a single-user, local tool.
- **Delete all** overwrites deleted data inside the database file (`secure_delete` + `VACUUM`). It can't control copies your operating system, backups or SSD wear-levelling may keep.
- The export is a helper for **your own** UC journal entries. It isn't connected to, or endorsed by, DWP, and you should check it before pasting.
