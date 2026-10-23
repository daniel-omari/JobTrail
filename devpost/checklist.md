---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast. The learner chose it: "just discuss and ask me for the important/core decisions".

## Slices

- [x] **1. Scan the synthetic inbox and see what was opened vs skipped**
  Becomes usable: A running JobTrail at `127.0.0.1:8000`. Clicking Scan Now processes the synthetic inbox with the rules only. Hiring emails from known platforms appear in a basic Tracker list, and the Privacy page shows the access ledger. Personal emails are skipped unopened.
  Why now: This is the kernel (privacy you can verify), and it bootstraps the whole stack: backend, DB, fixtures, frontend build, single-origin serving. Everything later plugs into this path.
  PRD ref: `prd.md > The Core Journey` (steps 1â€“4), `prd.md > Scanning`, `prd.md > Privacy`
  Spec ref: `spec.md > Inbox Source`, `spec.md > Gate`, `spec.md > Rules`, `spec.md > Extractor (Rules fallback)`, `spec.md > Scan Orchestrator`, `spec.md > Security Headers and Static Serving`, `spec.md > Synthetic Inbox Fixtures`, `spec.md > Data Model`, `spec.md > File Structure`
  Build: Scaffold `backend/` (pyproject, FastAPI app, sqlite schema, repo, logging) and `frontend/` (Vite React TS, router, NavBar with Scan Now, tokens.css, self-hosted Inter). Write the full `fixtures/inbox.json`. Implement the source, gate, rules, html_text, rules extractor and scan orchestrator (rules-only mode). Add the `/api/scan`, `/api/applications` and `/api/ledger` routes, CSP middleware and static serving. Add basic Tracker and Privacy pages.
  Verify (mechanical): `pytest` passes `test_rules`, `test_gate`, `test_canaries` (stub mode) and `test_egress`. `npm run build` succeeds. The app starts and `POST /api/scan` returns a summary with personal emails skipped and 0 ledger rows for them. The response headers include the CSP.
  Learner check: Run `python -m jobtrail`, click Scan Now, open the Tracker and Privacy pages, and check that no personal email appears in the ledger.
  Commit: `Scan synthetic inbox headers-first with gated, ledgered body access`

- [x] **2. The local AI extracts details, and the model is chosen**
  Becomes usable: Scans use Ollama for company/role/status, with strict JSON validation. If Ollama is off, a "rules-only mode" banner appears and scans still work. A probe script compares two candidate models.
  Why now: This is the riskiest unknown, covering the Ollama API shape, model quality and whether the "defences off" attack will land. It's better to find out before the defence demo is built on top of it.
  PRD ref: `prd.md > Scanning`, `prd.md > States and Boundaries` (Local AI not running)
  Spec ref: `spec.md > Extractor (LLM)`, `spec.md > External Services and Dependencies`, `spec.md > Important Failure Modes`, `spec.md > Decisions and Open Issues`
  Build: Add `extract_llm.py` (httpx â†’ `/api/chat`, `format` schema, temperature 0, 15s timeout, Pydantic validation), `/api/status`, the frontend banner, and `scripts/model_probe.py`. Pull two candidate models and run the probe. **Learner decides the model.**
  Verify (mechanical): `test_extraction` passes (bad, extra and out-of-enum output rejected). The probe prints per-model extraction accuracy on the hiring fixtures and whether the attack fooled each one with defences off. A scan with Ollama stopped shows the rules-only banner via `/api/status`.
  Learner check: Look at the probe output and choose the model. Stop Ollama, reload, and see the banner.
  Commit: `Add strict local-LLM extraction with rules-only fallback`

- [x] **3. The attack is caught: defences on/off and Quarantine**
  Becomes usable: With defences off, the hidden-text rejection becomes an Offer in the Tracker. With defences on, it lands in Quarantine with its reason, excerpt and an Info tip, and nothing else changes. Release (pre-filled from the rules) and Discard work. An amber banner shows while defences are off.
  Why now: This completes the kernel's second layer and the video's "oh, that's cool" beat. It's built before any polish.
  PRD ref: `prd.md > Quarantine`, `prd.md > Defence Demo`, `prd.md > Settings` (defences toggle)
  Spec ref: `spec.md > Detector`, `spec.md > Cross-check`, `spec.md > Scan Orchestrator`, `spec.md > Extractor (Rules fallback)`, `spec.md > Frontend Pages`
  Build: Add the detector and cross-check, the defences setting and its naive-prompt path, quarantine storage and API, the Quarantine page, a minimal Settings page with the defences toggle, and the banner.
  Verify (mechanical): `test_detector` and `test_defence_demo` pass (stub model scripted to obey the injection: off â†’ Offer, on â†’ quarantined, counts unchanged). A real-model run reproduces it locally.
  Learner check: Toggle defences off, scan, and see the false Offer. Delete it, toggle defences on, scan again, and open Quarantine.
  Commit: `Detect and quarantine injected emails with demo defences toggle`

- [x] **4. Overview dashboard with time filters**
  Becomes usable: Overview shows three half-circle gauges (sent, proceeding and rejected, in the agreed colours) with exact counts. This week (the default), This month and All time update them. There's an empty-state prompt, and a scan summary appears after Scan Now, along with the hover tooltip.
  Why now: This is the first screen of the journey and the main design surface, and design is judged. It goes before the early hands-on checkpoint so the look can be adjusted before the remaining pages copy it.
  PRD ref: `prd.md > Overview`, `prd.md > Look and Feel`, `prd.md > Scanning` (scan summary, tooltip)
  Spec ref: `spec.md > Frontend Pages`, `spec.md > Look and Feel`, `spec.md > Data Model` (Overview counts), `spec.md > API Layer`
  Build: Add `/api/overview?range=`, the event-based counting, the `Gauge` SVG component, the Overview page, filter buttons, Tooltip, the scan summary toast and the empty state.
  Verify (mechanical): An overview test checks that the counts per range match the fixture `_meta` expectations. The frontend builds, and the page renders with no console errors.
  Learner check: Early hands-on checkpoint, covering the whole app so far. Does it look and feel right?
  Commit: `Add Overview dashboard with range filters`

- [x] **5. Review queue for unknown senders**
  Becomes usable: Tier B emails (e.g. the recruiter on personal Gmail) appear in Review showing only the sender, subject and date. Approve reads the body, adds the application and trusts the sender. Reject leaves the email unopened forever. The nav shows a count badge.
  Why now: This is the last privacy-critical behaviour, and it depends on the scan pipeline from slices 1â€“3.
  PRD ref: `prd.md > Review`
  Spec ref: `spec.md > Rules`, `spec.md > Gate`, `spec.md > Data Model`, `spec.md > API Layer`
  Build: Add review queue storage and routes, trusted/rejected senders, the Review page and the badges.
  Verify (mechanical): The gate test is extended so that Review items have 0 ledger rows before approval and 1 after. A rejected sender isn't re-queued on rescan.
  Learner check: Scan, open Review, approve one email and reject another, then rescan.
  Commit: `Add header-only review queue with approve/reject`

- [x] **6. Full Tracker and Rejected/No Response archive**
  Becomes usable:
  - Stage badges and a detail drawer showing status history.
  - Manual add/edit/delete, and Don't track this.
  - An archive grouped by month (newest first) with Restore, Clear (keeps the last 7 days), Clear older than 30/90, and Force Clean (with a warning).
  - Ledger lines are redacted on clear.
  Why now: This builds on stored applications and events from earlier slices. It's mostly UI plus careful data rules.
  PRD ref: `prd.md > Tracker`, `prd.md > Privacy` (redaction)
  Spec ref: `spec.md > Applications Store`, `spec.md > Cleanup`, `spec.md > Frontend Pages`, `spec.md > API Layer`
  Build: Add the application CRUD routes, do-not-track, archive routes, cleanup functions with redaction, the Tracker page, the drawer, forms and ConfirmDialog.
  Verify (mechanical): `test_cleanup` covers the 7-day guard, redaction (sender and subject NULL) and do-not-track skips on rescan. The frontend builds.
  Learner check: Add, edit and delete an entry. Mark one "don't track". Clear the archive, and confirm the last week's rejections remain.
  Commit: `Add full tracker, archive tools and ledger redaction`

- [ ] **7. Privacy page complete and Delete all**
  Becomes usable: "Everything we hold about you" lists every stored item by type. Delete all (after a confirmation) wipes everything, including leftover text inside the DB file.
  Why now: This completes the trust story the video relies on ("prove it").
  PRD ref: `prd.md > Privacy`
  Spec ref: `spec.md > Cleanup`, `spec.md > API Layer`, `spec.md > Frontend Pages`
  Build: Add `/api/everything`, `/api/delete-all` (confirm, secure_delete, VACUUM) and the full Privacy page.
  Verify (mechanical): A test checks that after delete-all, every table is empty and the DB file bytes contain no previously stored company names.
  Learner check: Open Privacy, read what's held, Delete all, and confirm everything is empty.
  Commit: `Add everything-we-hold view and secure delete all`

- [ ] **8. Weekly UC journal export**
  Becomes usable: Export page with a week picker (defaulting to the last 7 days), a ready-to-paste summary with Copy, and Download CSV.
  Why now: This is the payoff beat. It only needs events data, which now exists.
  PRD ref: `prd.md > Export`
  Spec ref: `spec.md > Export`, `spec.md > API Layer`, `spec.md > Frontend Pages`
  Build: Add `export.py` and its route, plus the Export page.
  Verify (mechanical): `test_export` checks that the week's rejections are included after a normal Clear and that the CSV columns are correct.
  Learner check: Export this week, copy it, and download the CSV.
  Commit: `Add weekly UC journal export`

- [ ] **9. Settings and startup behaviour**
  Becomes usable: Excluded labels, scan on startup, auto-clean days (or never), and local AI status. `python -m jobtrail` runs auto-clean and the optional startup scan, then opens the browser.
  Why now: These are refinements on top of working features.
  PRD ref: `prd.md > Settings`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Rules`, `spec.md > Cleanup`, `spec.md > Where It Runs and How Someone Tries It`
  Build: Add the settings routes and the full Settings page, excluded-label handling in the rules, and the `__main__` startup tasks.
  Verify (mechanical): A test checks that an email with an excluded label is skipped with 0 ledger rows. Starting with scan-on-startup enabled produces a scan_runs row.
  Learner check: Exclude a label, rescan and see it skipped. Turn on scan on startup and restart.
  Commit: `Add settings, excluded labels and startup tasks`

- [ ] **10. Proof package: benchmark, CI, README**
  Becomes usable: `scripts/benchmark.py` prints the recall and privacy numbers. GitHub Actions runs the tests, the frontend build and the audits. The README explains what JobTrail is, how to run it, its privacy claims with their evidence, the numbers, and its limits.
  Why now: This packages the evidence once the features are stable, ready for `6-ship`.
  PRD ref: `prd.md > What We're Building`
  Spec ref: `spec.md > Proof of Privacy Tests`, `spec.md > Stack` (CI), `spec.md > Where It Runs and How Someone Tries It`
  Build: Add the benchmark script, `.github/workflows/ci.yml` and `README.md`.
  Verify (mechanical): The benchmark runs and its numbers match the fixture expectations. The full `pytest` run passes. The CI YAML is valid, and the act of pushing is left to `6-ship`.
  Learner check: Read the README's claims and check that each one has evidence behind it.
  Commit: `Add benchmark, CI workflow and README`

## Hands-on Checkpoints

- [x] Early usable behavior explored â€” after slice 4 (scan, ledger, attack demo, Overview look). Feedback: wanted one combined gauge, not three. Done: a segmented gauge with blue = awaiting reply, and a legend with counts.
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Final review complete â€” feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete â€” guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed â€” offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence:
Route and stops:
Edit outcome:
Reflection:
Activity mode:

## Revisions

- Fixture dates are stored as `days_ago` instead of absolute dates â€” absolute dates would go stale before judging, breaking the This week / This month views.
- Scan summary gained an `already_seen` count, so rescans don't report previously opened emails as "skipped unopened".
- Delete all (backend + Privacy button with confirm) was pulled forward from slice 7 into slice 3, because the defence demo needs a reset between the defences-off and defences-on runs. Slice 7 still adds the everything-we-hold view and the file-bytes test.
- The model comparison showed the hardened prompt alone did not stop the hidden-text attack once hidden text reached the model. This confirms the detector-before-model order. The real-model demo test (`pytest -m ollama`) passes with qwen2.5:7b.
- Overview changed from three gauges to one segmented gauge (learner feedback at the early checkpoint). Blue now means "awaiting reply" so the segments add up, and "new applications sent" is shown as a line below. PRD `Overview` and spec open issues updated.
- "Restore to Tracker" removes the misfiled Rejected/Closed event(s) rather than just un-archiving, so the Overview counts and export stay truthful. Redacted ledger lines also blank the stored company/role summary, not just the sender and subject.
