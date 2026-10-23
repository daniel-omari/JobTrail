---
doc: spec
status: approved
---

# JobTrail — Technical Spec

## How This Works, In Plain Language
JobTrail is a small web app that runs entirely on your PC. You open it in your browser at `http://127.0.0.1:8000`, an address only your own machine can reach.

- **The backend** is a Python program (FastAPI). It does all the real work: scanning the inbox, deciding what to open, talking to the local AI model, and saving results.
- **The frontend** is a React + TypeScript app: the pages you click around. It's compiled into plain files that the backend serves, so there is **one program, on one address**.
- **The inbox** is a JSON file of fake emails we write ourselves (the synthetic inbox). It sits behind an "inbox source" plug, so a real Gmail source can replace it later without changing anything else.
- **The gate** is the only way any code can read an email body. Before handing a body over, it writes an entry in the **access ledger**. Opening an email without logging it isn't possible, because no other route to a body exists.
- **The rules** decide everything about *what gets read*, using sender lists, subject keywords and labels. The AI never makes that decision.
- **The local AI model** (Ollama, running on your PC) is only asked to fill in three fields (company, role, status) for one email at a time. It's forced into a fixed JSON format, the answer is checked, and it has no tools.
- **The defences** sit between the email and the model:
  - an injection detector that runs before the model
  - output validation after it
  - a cross-check against what the rules saw.

  Anything suspicious goes to Quarantine instead of the Tracker.
- **The database** is a single SQLite file on your PC. It holds only the extracted fields, the ledger and your settings. Raw email bodies are never saved.
- **The proof** comes from automated tests that plant fake secrets in personal emails and check that they never show up in the database, the logs or any network request. The browser is also told, via a security header, to refuse any connection to another site.

Why this shape: one process and one data file is the smallest setup that still lets every privacy claim be checked. A separate server, accounts or cloud anything would add ways for data to leak without helping prove the idea.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. You start JobTrail (`python -m jobtrail`). The backend creates/opens `data/jobtrail.db`, runs **auto-clean** (archive entries older than N days, never the last 7), and, if **scan on startup** is on, runs a scan. Your browser opens at `127.0.0.1:8000` on **Overview**.
2. You click **Scan Now** → the frontend calls `POST /api/scan` → the **Scan orchestrator** asks the **inbox source** for *headers only*: id, sender, subject, date and labels for every email.
3. For each header, **Rules** decide:
   - **Skip, unopened:** an excluded label, a "don't track" match, a sender on the excluded/noise list, already processed, or no hiring signal. It's counted, and nothing else is stored.
   - **Review:** unknown sender with hiring keywords. Saved to the review queue (sender, subject, date). Not opened.
   - **Open:** a known recruiting platform or a trusted sender. Continue.
4. For "open": the **Gate** writes a ledger entry (sender, subject, rule matched), *then* returns the body.
5. With **defences on**:
   - The **Detector** checks the body for injection signs. If flagged → Quarantine (reason + short excerpt + rules-only pre-fill), and the model is never called.
   - Otherwise the **Extractor** sends the *visible* text, clearly marked as data, to Ollama with a strict JSON schema, then validates the answer.
   - The **Cross-check** compares the model's status with the rules' status evidence. A conflict (e.g. the body says "unfortunately" and the model says Offer) → Quarantine.
6. With **defences off** (demo only): no detector, no cross-check, and the raw body (hidden text included) is pasted straight into the prompt. Whatever the model says is saved, so the poisoned rejection becomes an Offer.
7. The result is saved as an application plus a status event. The ledger line is updated with *exactly what was stored*. The body variable goes out of scope and is never written anywhere.
8. The scan returns its summary ("Checked N · opened X · skipped Y unopened · Z for review · Q quarantined"). The frontend shows it and refreshes the gauges.
9. Tracker, Review, Quarantine, Privacy, Export and Settings each read from and write to the backend through `/api/...` routes.

```
Browser (React) ──/api──▶ FastAPI ──▶ Scan orchestrator
                                       │ headers only
                                       ▼
                         Inbox source (synthetic JSON) ◀── Gate (logs to ledger, then returns body)
                                       │
                         Rules ─▶ Detector ─▶ Extractor (Ollama @127.0.0.1:11434) ─▶ Cross-check
                                       │
                                       ▼
                                 SQLite (data/jobtrail.db)
```

## Stack
| Part | Choice | Why |
|---|---|---|
| Language (backend) | **Python 3.14** (fallback to 3.13 via `py -3.13` if a library misbehaves) | Daniel's strongest language; already installed. **Verify early** that FastAPI/Pydantic install cleanly on 3.14. |
| Web framework | **FastAPI** + **Uvicorn** | Daniel's brief choice. Typed request/response models, automatic API docs. [docs](https://fastapi.tiangolo.com/) |
| Validation | **Pydantic v2** (comes with FastAPI) | Strict model-output validation (fixed fields, status enum, length caps, no extra keys). [docs](https://docs.pydantic.dev/) |
| Database | **SQLite via the stdlib `sqlite3` module** | A single local file with no server. Plain SQL in one module is easy to read and explain in interviews, and needs no ORM. [docs](https://docs.python.org/3/library/sqlite3.html) |
| HTTP to Ollama | **httpx** | Simple, well-tested; easy to stub in tests. [docs](https://www.python-httpx.org/) |
| Local AI | **Ollama** + a small model, picked in an early build test (candidates: a ~3B and a ~8B instruct model) | Learner choice: nothing leaves the machine. Structured outputs force JSON matching a schema. [docs](https://docs.ollama.com/) · [structured outputs](https://docs.ollama.com/capabilities/structured-outputs) · [API](https://github.com/ollama/ollama/blob/main/docs/api.md) |
| Frontend | **React + TypeScript + Vite** | **Learner choice:** more polished, judged on design. Accepted trade-off: a build step and an npm dependency tree, mitigated below. [React](https://react.dev/) · [Vite](https://vite.dev/) |
| Routing | **React Router** | One URL per page (Overview, Tracker, …). [docs](https://reactrouter.com/) |
| Styling | Plain CSS with CSS variables; **self-hosted Inter font** via `@fontsource/inter` | No CDN, no UI kit, full control over the Malwarebytes/Indeed look. [Fontsource](https://fontsource.org/fonts/inter) |
| Charts | **Hand-written SVG half-circle gauges** | Avoids a chart library and the extra dependencies that would come with it. |
| Tests | **pytest** (backend), **Vitest** for a few frontend unit tests (optional) | Canary, rules, detector, extraction-validation and egress tests. [pytest](https://docs.pytest.org/) |
| CI | **GitHub Actions**: pytest + `npm ci && npm run build` + `npm audit --audit-level=high` + `pip-audit` | Repeatable proof on every push. |

Unverified, to check in the first build step: Python 3.14 wheel support for the pinned FastAPI/Pydantic/httpx versions, the current Ollama structured-output request field (`format` taking a JSON schema), and which small models are currently available in the Ollama library.

## Where It Runs and How Someone Tries It
- **Runtime:** a local process on Windows (also works on macOS/Linux). The backend binds to **127.0.0.1 only**.
- **Requirements:** Python 3.14 (or 3.13), Node 24 (only to build the frontend), Ollama with the chosen model pulled. No API keys, accounts or `.env` secrets.
- **First-time setup:**
  ```
  cd frontend && npm ci && npm run build      # compiles React into frontend/dist
  cd ../backend && py -m venv .venv && .venv\Scripts\activate && pip install -e .[dev]
  ollama pull <chosen-model>
  ```
- **Run:** `python -m jobtrail` → opens `http://127.0.0.1:8000`. Without Ollama running, it starts in rules-only mode.
- **Dev mode (building only):** `npm run dev` (Vite on :5173, proxying `/api` to :8000) plus `uvicorn jobtrail.main:app --reload`. Not used for the demo.
- **Tests:** `pytest` in `backend/`. These run without Ollama, using a stub model. Real-model tests are marked `@pytest.mark.ollama` and only run locally.
- **Demo recording** (for `6-ship`): fresh DB → Overview (empty) → Scan Now (defences off) → show the false Offer → Delete all → Settings: defences on → Scan Now → Quarantine → Privacy ledger → `pytest` canary run in a terminal → DevTools Network tab showing only `127.0.0.1` → Export.
- **Submission:** demo video plus a public GitHub repo. **No deployment** (learner choice; a hosted copy would contradict local-first).

## Look and Feel
Implements `prd.md > Look and Feel`.
- **Theme:** light only. Page background `#f7f8fa`, cards white with a 1px `#e3e6eb` border, soft shadow, 12px radius. Generous spacing, one column of content plus a top nav. Calm "security tool" clarity (Malwarebytes) with friendly readability (Indeed).
- **Status colours** (CSS variables):
  - `--sent: #2563eb` (blue)
  - `--proceeding: #16a34a` (green)
  - `--rejected: #cf2344`
  - The archive uses a muted variant of rejected.
- **Typography:** Inter, self-hosted. 15–16px body, large bold numbers on the gauges, sentence-case headings.
- **Nav bar:** white, with the JobTrail wordmark on the left, then the page links, and **Scan Now** as the one solid primary button on the right. Review and Quarantine links show count badges.
- **Copy tone:** plain British English, calm and factual. Never "secure"; say "designed to minimise data, verified by tests". Warnings explain rather than alarm.
- **Components:**
  - **Tooltip:** shows after ~1s on hover or focus.
  - **Confirm dialog:** used for Delete all and Force Clean.
  - **Banner:** used for rules-only mode and defences off. The defences-off banner is a persistent amber "Defences are OFF (demo mode)" strip across the top, so a recording can never be mistaken for a normal run.

## Components

### Inbox Source
- **Interface (`InboxSource`):**
  - `list_headers() -> list[Header]`, where `Header` = id, sender, display name, subject, date, labels.
  - `_read_body(id) -> Body`, private: only the Gate calls it.
- **`SyntheticInbox`** loads `fixtures/inbox.json`. The interface is shaped like Gmail's (labels, message ids) so a Gmail source fits later.
- PRD ref: `prd.md > Scanning`.

### Gate
- The only path to a body. `open(header, rule) -> Body`:
  1. Inserts a ledger row (message id, sender, subject, rule, `stored=pending`).
  2. Then calls `_read_body`.
- Any code that needs a body must go through it. A test asserts that the number of bodies read equals the number of ledger rows.
- PRD ref: `prd.md > Privacy`, `prd.md > Scanning`.

### Rules
Pure functions, no I/O.
- **`classify(header, settings) -> Decision`**, one of:
  - **SKIP**, with reason: `excluded_label`, `do_not_track`, `noise_sender`, `already_seen`, `no_signal`
  - **REVIEW**
  - **OPEN**, with rule: `known_platform` / `trusted_sender`.
- **Sender lists:**
  - Tier A allowlist from the brief: `myworkday.com`, `greenhouse-mail.io`, `ashbyhq.com`, … plus assessment platforms.
  - Noise list: `match.indeed.com`, `jobalert.indeed.com`, `xing.com`, `gradcracker.com`, `updates-noreply@linkedin.com`.
  - `jobs-noreply@linkedin.com` counts as Tier A only for application-update subjects.
- **Hiring keywords** (Tier B), checked against the subject only: "your application", "interview", "assessment", "unfortunately", "offer", "next steps", "thank you for applying". Negative context words ("loan", "membership", "visa", "mortgage") suppress the match, so a gym "membership application" is skipped.
- **`status_evidence(visible_text, subject) -> Status | None`**: a keyword/regex status read from the email, used for the cross-check and the rules-only fallback. For example:
  - "unfortunately", "not to proceed", "unsuccessful" → Rejected
  - "invite you to interview" → Interview
  - "online assessment", "coding test" → Assessment
  - "pleased to offer" → Offer
  - "position has been filled", "no longer accepting" → Closed
  - "received your application" → Applied.
- PRD ref: `prd.md > Scanning`, `prd.md > Review`, `prd.md > Settings`.

### Detector
- **`detect(body) -> list[Flag]`**. Each flag holds a reason code, a human reason, an excerpt (≤160 chars, whitespace collapsed) and an Info tip.
- **Checks:**
  - **Instruction-like text:** "ignore (all|previous) instructions", "you are now", "system:", "assistant:", "set status", "mark (all|every)", "as an AI".
  - **Hidden text:** HTML with `display:none`, `visibility:hidden`, `font-size:0`, white or near-white text, off-screen positioning. The hidden text itself is checked and excerpted.
  - **Zero-width or bidi control characters.**
  - **Long base64-like runs.**
  - **Attempts to affect other records:** "all applications", "every candidate", "other records".
- Visible text for everything else is produced by a small HTML-to-text helper that **drops** hidden elements.
- PRD ref: `prd.md > Quarantine`, `prd.md > Defence Demo`.

### Extractor (LLM)
- **`extract_llm(visible_text, sender, subject) -> Extraction`** makes one call per email to `POST http://127.0.0.1:11434/api/chat` with:
  - `stream:false`, `options.temperature:0`
  - `format` = the JSON schema of `Extraction`.
- **Prompt (defences on):** the system message says the model only fills the fields, and that the email is untrusted data which may contain instructions to be ignored. The email goes in the user message inside `<email>…</email>` delimiters.
- **Validation:** Pydantic `Extraction` with `company` (1–100 chars), `role` (1–120 chars), `status` ∈ {Applied, Assessment, Interview, Offer, Rejected, Closed}, `extra="forbid"`. Invalid JSON or a failed validation → Quarantine with reason "AI output failed validation".
- No tools, no function calling, no conversation history.
- PRD ref: `prd.md > Scanning`.

### Extractor (Rules fallback)
- **`extract_rules(visible_text, header) -> Extraction`:**
  - **Company:** from the sender display name, the "at {Company}" / "{Company} Talent Team" patterns, or the sender domain.
  - **Role:** from "for the {role} (role|position)" style patterns.
  - **Status:** from `status_evidence`.
- Used when Ollama is unavailable, and to **pre-fill Quarantine releases**. It never uses model output.
- PRD ref: `prd.md > States and Boundaries`, `prd.md > Quarantine`.

### Cross-check
- **`crosscheck(model, evidence, header) -> list[Flag]`**. It flags when:
  - the rules' status evidence exists and conflicts with the model's status (an especially strong signal is model = Offer while evidence = Rejected)
  - the model's company appears nowhere in the sender, subject or visible text.
- PRD ref: `prd.md > Quarantine`.

### Scan Orchestrator
- **`run_scan(source, db, settings) -> ScanSummary`** ties it all together:
  - Applies the `defences` setting: **off** = naive prompt with the raw body (hidden text included), no detector or cross-check, and the model output is trusted after a JSON parse.
  - Deduplicates by a SHA-256 of the message id stored in `seen_messages`.
  - Only aggregate counts are kept for skipped emails.
  - Logs only event types and message-id hashes, never subjects or bodies.
- PRD ref: `prd.md > Scanning`, `prd.md > Defence Demo`.

### Applications Store
- `repo.py`: all SQL in one module, covering applications, events, archive moves, restore, manual add/edit/delete, and do-not-track.
- A Rejected or Closed event moves an application to the archive.
- PRD ref: `prd.md > Tracker`.

### Cleanup
- **`clear(older_than_days)`:** never deletes anything with an event in the last 7 days.
- **`force_clean()`:** deletes the whole archive; the API requires `confirm=true`.
- **Auto-clean** runs on startup using `settings.auto_clean_days` (default 90, or `null` = never).
- Clearing **redacts** the matching ledger rows: sender and subject are set to NULL, `redacted=1`, and the date and rule are kept.
- **`delete_all()`:** deletes every row in every table, then runs `VACUUM` with `PRAGMA secure_delete=ON`, so deleted text doesn't linger in the file.
- PRD ref: `prd.md > Tracker`, `prd.md > Privacy`.

### Export
- **`weekly_summary(start, end) -> text`** produces one line per event in range: date, employer, role, how applied (the source platform, e.g. "Online via Workday", or the user's value for manual entries) and outcome.
- **`weekly_csv(start, end)`** produces the same data as CSV.
- It reads events, so normally-cleared archive items (always older than 7 days) don't affect the current week.
- PRD ref: `prd.md > Export`.

### API Layer
FastAPI routes under `/api`, all JSON, Pydantic request/response models:

| Route | Purpose |
|---|---|
| `GET /api/overview?range=week\|month\|all` | the three counts |
| `POST /api/scan` | → ScanSummary |
| `GET/POST/PATCH/DELETE /api/applications`, `POST /api/applications/{id}/restore`, `POST /api/applications/{id}/do-not-track` | Tracker |
| `GET /api/archive`, `POST /api/archive/clear?older_than=7\|30\|90`, `POST /api/archive/force-clean` | Archive |
| `GET /api/review`, `POST /api/review/{id}/approve\|reject` | Review |
| `GET /api/quarantine`, `POST /api/quarantine/{id}/release` (body: user-confirmed fields), `POST /api/quarantine/{id}/discard` | Quarantine |
| `GET /api/ledger`, `GET /api/everything`, `POST /api/delete-all` (confirm=true) | Privacy |
| `GET /api/export?start=&end=&format=text\|csv` | Export |
| `GET/PUT /api/settings`, `GET /api/status` (Ollama available? model name? defences on?) | Settings |

PRD ref: all `prd.md > Features and Behavior` headings.

### Security Headers and Static Serving
- Middleware adds:
  - `Content-Security-Policy: default-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`
  - `Referrer-Policy: no-referrer`
  - `X-Content-Type-Options: nosniff`
- FastAPI serves `frontend/dist` at `/` with an SPA fallback to `index.html`.
- Uvicorn binds `127.0.0.1`.
- PRD ref: `prd.md > States and Boundaries` (nothing leaves the machine).

### Frontend Pages
React Router routes, each page a component that fetches from `/api`:

| Page | Implements |
|---|---|
| `Overview` | three half-circle `Gauge` SVGs with counts on top; This week / This month / All time buttons (week is the default); empty state; the scan summary toast. Implements `prd.md > Overview`. |
| `Tracker` | Active table (stage badges, row → detail drawer with history); Add/Edit/Delete; Don't track this; Rejected / No Response archive grouped by month, newest first, with Restore / Clear / Clear older than… / Force Clean (confirm dialog). Implements `prd.md > Tracker`. |
| `Review` | sender/subject/date list; Approve / Reject. Implements `prd.md > Review`. |
| `Quarantine` | reason, excerpt, Info tip; Release (form pre-filled from the rules) / Discard. Implements `prd.md > Quarantine`. |
| `Privacy` | ledger table, Everything-we-hold view, Delete all (confirm). Implements `prd.md > Privacy`. |
| `Export` | week picker (default last 7 days), summary text with Copy, Download CSV. Implements `prd.md > Export`. |
| `Settings` | excluded labels, scan on startup, auto-clean days/never, Demo: defences toggle, local AI status. Implements `prd.md > Settings`. |

Shared components: `NavBar` (with ScanNow + Tooltip), `Gauge`, `StageBadge`, `ConfirmDialog`, `Banner`, `EmptyState`. One `api.ts` holds the typed fetch calls.

## Data Model
SQLite file `backend/data/jobtrail.db` (gitignored). All tables are cleared by Delete all.

| Table | Columns | Updated by | Persists? |
|---|---|---|---|
| `applications` | id, company, role, source (platform/manual), how_applied, current_status, archived (0/1), manual (0/1), created_at, updated_at | scan, manual edits, archive moves | yes |
| `events` | id, application_id, status, event_date, message_hash (nullable) | each extracted email or manual stage change | yes, and drives Overview ranges and Export |
| `ledger` | id, opened_at, message_hash, sender, subject, rule, stored_summary, redacted | Gate (insert), orchestrator (stored_summary), cleanup (redact) | yes |
| `seen_messages` | message_hash, outcome (opened/rejected_review/quarantined) | orchestrator, review | yes (hash only) |
| `review_queue` | id, message_id, sender, subject, received_date | orchestrator; removed on approve/reject | until handled |
| `quarantine` | id, message_id, sender, subject, reasons (JSON), excerpt (≤160 chars), rules_prefill (JSON) | orchestrator; removed on release/discard | until handled |
| `trusted_senders` / `rejected_senders` | address | review approve/reject | yes |
| `do_not_track` | company, role | Tracker action | yes |
| `settings` | key, value | Settings page | yes |
| `scan_runs` | id, ran_at, checked, opened, skipped, review, quarantined, mode (llm/rules), defences | orchestrator | yes (counts only) |

**Overview counts** for a range:
- **sent** = distinct applications whose *first* event falls in the range. This is usually the `Applied` confirmation; if the first email seen is an interview invite, that still counts as an application sent.
- **proceeding** = distinct applications with an Assessment/Interview/Offer event in the range
- **rejected** = distinct applications with a Rejected/Closed event in the range
- **all time** includes archived applications.

**Leaving and coming back:** everything above stays in the file between runs. Nothing lives only in the browser except the selected Overview filter, which resets to "This week" on launch.

## File Structure
```
jobtrail/                          # repo root
├── backend/
│   ├── pyproject.toml             # deps + pytest config
│   ├── jobtrail/
│   │   ├── __main__.py            # `python -m jobtrail`: startup tasks, uvicorn on 127.0.0.1, open browser
│   │   ├── main.py                # FastAPI app, security-header middleware, static serving
│   │   ├── config.py              # paths, Ollama URL/model, defaults
│   │   ├── db.py                  # connection, schema creation, pragmas
│   │   ├── repo.py                # all SQL queries
│   │   ├── models.py              # Pydantic models (Extraction, API shapes, Status enum)
│   │   ├── logging_setup.py       # logs event types + hashes only
│   │   ├── sources/
│   │   │   ├── base.py            # InboxSource interface, Header/Body types
│   │   │   └── synthetic.py       # loads fixtures/inbox.json
│   │   ├── pipeline/
│   │   │   ├── gate.py            # ledger-first body access
│   │   │   ├── rules.py           # tiers, sender lists, keywords, status evidence
│   │   │   ├── html_text.py       # visible-text extraction (drops hidden elements)
│   │   │   ├── detector.py        # injection flags + excerpts + Info tips
│   │   │   ├── extract_llm.py     # Ollama call + validation
│   │   │   ├── extract_rules.py   # rules-only extraction / quarantine pre-fill
│   │   │   ├── crosscheck.py      # model vs rule evidence
│   │   │   └── scan.py            # orchestrator, defences on/off
│   │   ├── cleanup.py             # clear / force clean / auto-clean / delete all / redaction
│   │   ├── export.py              # UC summary text + CSV
│   │   └── api/                   # route modules: overview, scan, applications, review,
│   │                              #   quarantine, privacy, export, settings
│   ├── fixtures/
│   │   └── inbox.json             # synthetic inbox: ~15 hiring, ~10 personal (canaries), ~6 noise, ~4 malicious
│   ├── tests/
│   │   ├── conftest.py            # temp DB, stub Ollama, egress guard
│   │   ├── test_rules.py
│   │   ├── test_detector.py
│   │   ├── test_extraction.py     # validation rejects bad/extra fields
│   │   ├── test_gate.py           # bodies read == ledger rows; Review items unopened
│   │   ├── test_canaries.py       # secrets never in DB file, log file, or Ollama requests
│   │   ├── test_egress.py         # any non-localhost connection fails the test
│   │   ├── test_defence_demo.py   # off → Offer; on → quarantined, counts unchanged
│   │   ├── test_cleanup.py        # 7-day guard, redaction, delete all empties DB
│   │   └── test_export.py
│   ├── scripts/
│   │   └── benchmark.py           # recall + privacy numbers for README
│   └── data/                      # jobtrail.db + jobtrail.log (gitignored)
├── frontend/
│   ├── package.json / package-lock.json / vite.config.ts / tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx / App.tsx     # router + layout
│       ├── api.ts                 # typed fetch calls
│       ├── styles/                # tokens.css (colours, spacing), global.css
│       ├── components/            # NavBar, Tooltip, Gauge, StageBadge, ConfirmDialog, Banner, EmptyState
│       └── pages/                 # Overview, Tracker, Review, Quarantine, Privacy, Export, Settings
├── .github/workflows/ci.yml       # pytest, frontend build, npm audit, pip-audit
├── devpost/                       # scope.md, prd.md, spec.md, checklist.md (learner-profile.md gitignored)
├── README.md                      # what, why, how to run, privacy claims + evidence, benchmark numbers, limits
└── .gitignore
```

## Synthetic Inbox Fixtures
Implements `scope.md > The POC Boundary`.
- **Format:** `fixtures/inbox.json` is a list of `{id, from, from_name, subject, date, labels[], body_html|body_text, _meta:{kind, expected}}`. `_meta` is for tests and the benchmark only; the app ignores it.
- **Kinds:**
  - `hiring` (~15), including the tricky ones: a recruiter on personal Gmail (→ Review), a plain-text agency email, and a rejection with a "Thank you for applying" subject.
  - `personal` (~10), each with a unique canary like `CANARY-BANK-7Q2X`.
  - `noise` (~6): job alerts, a loan or gym "application".
  - `malicious` (~4): a visible injection, a hidden-text "offered the role" rejection, a fake "SYSTEM:" message, and a "mark all applications" attempt.
- Dates are spread around "today", so the This week / This month filters show different numbers.
- All companies and people are fictional.

## External Services and Dependencies
- **Ollama (local):** `POST http://127.0.0.1:11434/api/chat`.
  - Payload: `{model, messages:[system,user], format:<JSON schema>, stream:false, options:{temperature:0}}`.
  - Response: `{message:{content:"<json string>"}, ...}`.
  - Availability check: `GET /api/tags`.
  - No key, no cost, no rate limit. [API docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- **No other external service.** No accounts, keys or telemetry.
- **npm/PyPI:** only at install time. Versions are pinned via `package-lock.json` and `pyproject.toml`.

## Proof of Privacy Tests
Implements `scope.md > The Unique Kernel`.
- **Canary test:** runs a full scan (stub model) and then searches the raw bytes of `jobtrail.db` (after a checkpoint), `jobtrail.log`, and every captured request body sent to the stub Ollama for each canary string. The test fails on any hit. A second variant runs with the real model locally.
- **Egress test:** `conftest.py` patches `socket.socket.connect` so that any address other than `127.0.0.1`/`localhost` raises an error and fails the test. The whole suite runs under this guard.
- **Gate test:** the count of bodies read equals the count of ledger rows. Review items, skipped and personal emails have no ledger rows.
- **Benchmark script:** prints "Caught X of Y hiring emails (recall)" and "Opened 0 of Z personal emails (privacy)" for the README.

## Important Failure Modes
- **Ollama not running or the model not pulled** → `/api/status` reports unavailable. A "Local AI unavailable — running in rules-only mode" banner shows, and scans use `extract_rules`.
- **The model returns junk or times out (15s)** → that email is quarantined with "AI output failed validation". The scan continues.
- **The defences-off attack doesn't fool the chosen model** → found during the model test step. We adjust the attack email or pick the model that falls for it, and record which in the README. We never fake the "off" result.
- **Frontend not built** → the backend serves a plain page saying "Run `npm run build` in frontend/".

## What Was Simplified and Why
- **Synthetic JSON inbox** instead of Gmail: proves the pipeline without OAuth or restricted scopes. A Gmail source would implement the same `InboxSource` interface.
- **Scan on startup** instead of scheduled scans: no background service needed. (Learner choice in the PRD.)
- **Stdlib `sqlite3`** instead of an ORM: fewer dependencies, explicit SQL.
- **Hand-drawn SVG gauges** instead of a chart library: fewer npm dependencies, full styling control.
- **Single-process demo build** (FastAPI serves the built React app) instead of two servers: one origin, so the CSP and egress story is simpler.
- **Stub model in CI:** GitHub runners have no GPU or Ollama. Real-model tests run locally and are noted in the README.

## Decisions and Open Issues
**Learner decisions:**
- **React + TypeScript (Vite)** for polish. Accepted trade-off: a build step and npm dependencies, mitigated by CSP, self-hosted assets, a single-origin build, minimal deps and `npm audit`.
- **Local Ollama.** Agreed to install it and to pick the model through an early test.
- **No deployment;** local app + recording.

**Agent recommendations in this draft** (accepted unless changed at review):
- stdlib `sqlite3`
- httpx
- hand-drawn gauges
- Inter via Fontsource
- defences-off = naive prompt + no detector/cross-check
- detector runs *before* the model, so flagged emails never reach it
- SHA-256 message hashes for dedupe
- `secure_delete` + `VACUUM` on Delete all.

**Learner uncertainty discussed:** *"Why does React make 'nothing leaves your machine' harder to defend, and how do we resolve it?"*
- **Clarified:** the risk is browser-side requests (fonts, CDNs, analytics), a second dev process and npm supply chain.
- **Resolved by:** a CSP `connect-src 'self'`, self-hosted assets, FastAPI serving the built app on one origin bound to 127.0.0.1, minimal deps plus audits, and the backend egress-guard test.
- **Evidence during the build:** DevTools Network shows only `127.0.0.1`; the response headers show the CSP; `test_egress.py` passes.

**Open, to check early in the build:**
- Python 3.14 compatibility of the pinned deps (fallback: 3.13).
- The current Ollama structured-output field and docs URL.
- Model choice (the ~3B vs ~8B test).

**Carried from the PRD:**
- One gauge per count vs a single segmented half-circle. Planned as **one gauge per count**; the PRD says it can wait for the build.

**Hackathon requirement:** `scope.md`, `prd.md` and `spec.md` live in `devpost/`. Confirm in `6-ship` that this placement satisfies "the repo must include" them (copy them to the repo root if needed).
