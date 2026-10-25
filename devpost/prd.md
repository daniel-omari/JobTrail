---
doc: prd
status: approved
---

# JobTrail — Product Requirements

A local-first job application tracker for UK job seekers and UC claimants. It reads only hiring emails, logs applications automatically, shows exactly what it touched, and exports a weekly UC journal summary.
Source: `scope.md > The Unique Kernel`, `scope.md > Who It's For`.

## The Core Journey
Source: `scope.md > The Core Loop`, `scope.md > What "Working" Looks Like`.

1. The user opens JobTrail and lands on **Overview**. On first use it's empty, with a prompt to run a first scan.
2. They hover over **Scan Now** and a tooltip explains what it does. They click it.
3. JobTrail checks **headers only** (sender, subject, date, labels) for every email:
   - known recruiting platform → body opened, details extracted
   - unknown sender with hiring signals → sent to **Review** (unopened)
   - excluded label / "don't track" / everything else → skipped, **never opened**.
4. A scan summary appears and the Overview gauges update (blue sent / green proceeding / red rejected).
5. The user opens **Tracker** to see each application and its stage ("Stage: Interview!"), and edits, adds or removes entries if needed.
6. They handle **Review** (approve or reject unknown senders) and check **Quarantine** (flagged emails, with the reason and an excerpt).
7. They open **Privacy** to see the ledger of every email opened and why, and everything JobTrail holds.
8. Once a week, they open **Export** and copy the UC journal summary (or download a CSV).

**Success:** the tracker is accurate, private emails show as skipped unopened, and the malicious email is contained.

## Screens and Layout
A top navigation bar on every page: **Overview · Tracker · Review · Quarantine · Privacy · Export · Settings**. Each is its own page. Review and Quarantine show a count badge when items are waiting. **Scan Now** is always visible in the top bar.

## Look and Feel
- Light/white theme only, with no dark mode. Readability comes first.
- References: **Malwarebytes** (simple, clean, security-tool clarity, minimal clutter) and **Indeed.com** (light, friendly, readable).
- Status colours:
  - **Applications sent:** blue
  - **Rejections:** `#cf2344`
  - **Proceeding** (Assessment / Interview / Offer): green
- The Overview is minimal: half-circle gauges with exact counts shown on top, and no other detail.
- Warnings and quarantine use clear but calm wording, never alarmist.

## Features and Behavior

### Overview
- **One half-circle gauge split into three coloured segments** that add up to the whole, so the proportions are visible at a glance (revised at the build's early hands-on check):
  - **Proceeding** (green): current stage Assessment, Interview or Offer.
  - **Awaiting reply** (blue): sent, no outcome yet.
  - **Rejected / no response** (`#cf2344`): Rejected or Closed.
- The centre shows the total number of applications with activity in the period. A legend shows each segment's exact count. A line below shows **new applications sent** in the period.
- **Time filter buttons:** **This week** (the default when the app opens) · **This month** · **All time**. Clicking one updates the gauge straight away. The active button is highlighted.
  - This week = Monday to today. This month = the calendar month. All time = all Tracker data, including the archive.
  - An application counts in a period if any of its events happened in that period. It is coloured by its current stage. "New applications sent" counts applications whose first event falls in the period.
- The empty state reads "No applications yet. Run your first scan", next to the Scan Now button.
- [ ] After scanning the synthetic inbox, the three segments add up to the total and match the fixture expectations.
- [ ] Switching filters changes the counts to match the fixture dates, and "This week" is selected on launch.

### Scanning
Source: `scope.md > The POC Boundary`.
- **Scan Now** has a hover tooltip (about one second) saying, for example: "Checks email headers for job-application updates. Only hiring emails are opened."
- **Stage 1 (headers only):** emails with excluded labels or "don't track" matches, and emails with no hiring signal, are skipped without being opened.
- **Stage 2:** for known recruiting platforms, the body is read, the local AI model extracts company / role / status into a fixed format, and the result is cross-checked against the rules. The raw body is then discarded.
- Unknown senders with hiring signals go to Review. They are **not opened**.
- **Scan summary** after each run: "Checked N emails · opened X · skipped Y unopened · Z waiting for review · Q quarantined".
- Rescanning doesn't create duplicates; an email already processed is not reprocessed.
- [ ] No canary secret from a personal email appears anywhere in the app, its storage, logs or network traffic.
- [ ] Skipped emails appear in the ledger counts as "skipped unopened", with no body ever read.

### Tracker
- **Active applications** list. Each row shows:
  - company, role, a **stage badge** ("Stage: Interview!", "Stage: Assessment", "Stage: Offer!", "Still pending reply…")
  - date applied, date of the last update, and the source platform.
- Click a row for details: its status history (e.g. Applied 3 Oct → Assessment 8 Oct) and which email(s) it came from.
- **Add entry** manually: company, role, stage and date. Manual entries are marked as manual.
- **Edit** or **delete** any entry.
- **Search** by company, role or notes, filtering both the active list and the archive (added at final review).
- **Notes:** the user's own private notes per application (e.g. "Interview Thu 2pm"). Shown in the drawer and in "everything we hold", never in the export (added at final review).
- **Don't track this:** removes the entry, and future emails about that same application (same company + role) are skipped unopened.
- **Rejected / No Response** archive, a separate section of the Tracker:
  - Rejected and Closed applications move here automatically.
  - Sorted **newest first, grouped by month**.
  - **Restore to Tracker** returns a misfiled entry to the active list.
  - **Clear** removes entries older than 1 week, deliberately keeping the last week's for the UC export.
  - **Clear older than…** works the same way for 30 or 90 days.
  - **Force Clean** removes everything, after a pop-up warning that this week's rejections will disappear from the UC export.
- [ ] A rejection email moves its application from Active to the archive.
- [ ] Clear leaves entries from the last 7 days in place.

### Review
Source: `scope.md > The POC Boundary` (minimal review queue).
- Lists Tier B emails showing **only the sender, subject and date**. The body is never shown or read before approval.
- **Approve:** JobTrail reads the body, extracts the details as normal, and remembers the sender as trusted for future scans.
- **Reject:** the email is never opened, and that sender is not offered for review again.
- The empty state reads "Nothing to review".
- [ ] Before approval, the ledger shows no "opened" entry for a Review item.

### Quarantine
Source: `scope.md > The Unique Kernel` (second layer).
- Lists flagged emails, each with:
  - the **reason** ("instruction-like text detected", "hidden text", "AI output disagrees with rule evidence")
  - a **short excerpt** of the flagged text (capped length)
  - an **"Info:"** tip explaining in plain English what the attack tried to do and why it was stopped.
- **Release:** opens the entry **pre-filled from rules only**, never from the AI model's output. The user confirms or edits it before it's saved.
- **Discard:** removes it from Quarantine, and nothing is saved to the Tracker.
- The empty state reads "No threats detected".
- [ ] With defences on, the malicious "offered the role" rejection email lands here and the Overview counts don't change.

### Privacy
Source: `scope.md > The Unique Kernel`.
- **Access ledger:** one line per email opened, showing the date, sender, subject, **why** it was opened (the rule that matched), and **exactly what was stored**. Skipped emails are shown as counts, not listed with details.
- **Everything we hold about you:** a complete view of every stored item (applications, ledger entries, quarantine excerpts, settings).
- **Delete all** wipes everything, after a confirmation pop-up.
- **Reset scan data** (demo mode only) clears scanned data but keeps Settings, for re-running the demo.
- When an archived record is cleared, its ledger line is **redacted**: it keeps the date and the rule (e.g. "Opened 1 email · 12 Oct · rule: known ATS") but drops the sender and subject.
- [ ] After Delete all, "Everything we hold" is empty.

### Export
Source: `scope.md > The Core Loop`.
- Pick a week (default: the last 7 days).
- A ready-to-paste **UC journal summary**: date, employer, role, how applied, outcome. One-click **Copy**.
- **Download CSV** of the same data.
- [ ] The export includes rejections from that week, even after a normal Clear.

### Settings
- **Excluded labels:** the user lists labels/categories (e.g. "Personal", "Banking") that are never checked.
- **Scan on startup:** on or off.
- **Auto-clean:** archive entries older than N days are removed automatically. Default 90, user-adjustable, or Never. It never touches the last 7 days.
- **Demo: defences on/off**, clearly labelled as a demonstration control. It appears **only in demo mode** (`--demo`); a normal run always has defences on (revised at final review).
- **Local AI status:** shows whether the local model is available.

### Defence Demo
Source: `scope.md > What "Working" Looks Like`.
- A synthetic **rejection** email contains hidden text claiming the candidate was offered the role.
- **Defences off:** the tracker logs an **Offer** and the green Proceeding count goes up.
- **Defences on:** the email is quarantined with its reason and excerpt, and no counts change.
- [ ] Both runs can be shown back-to-back in the video.

## States and Boundaries
- **First use:** all pages are empty with friendly prompts, and Overview points to Scan Now.
- **Local AI not running:** a banner reads "Local AI unavailable — running in rules-only mode". Scans still work using rules alone.
- **Scan finds nothing new:** the summary reads "No new updates".
- **What persists:** applications, ledger, Review decisions, the trusted-sender list, quarantine excerpts and settings, until the user clears them or uses Delete all.
- **What never persists:** raw email bodies, and emails that were skipped (only aggregate counts are kept).
- **Boundaries:** single user on one machine. Nothing leaves the machine. Read-only access to email.

## Product Decisions
- **Overview shows counts only; details live in the Tracker.** Keeps the dashboard minimal.
- **Overview time filter: This week (default) / This month / All time.** Lets the user see just this past week at a glance.
- **A single segmented gauge instead of three.** The colours exist to compare outcomes on one graph. Blue therefore means "awaiting reply", so the segments add up; the sent count moved to a line below.
- **Proceeding = Assessment, Interview and Offer combined on the Overview.** Keeps it simple; the Tracker badge shows the exact stage.
- **Rejected/Closed go to a separate archive, newest first, grouped by month.** The list gets big; it acts like an organised recycling bin.
- **Clear keeps the last week by default, and Force Clean warns.** Protects the UC export.
- **Auto-clean defaults to 90 days, with a custom value or Never allowed.** Avoids losing recent data.
- **Review shows headers only; the body is read only after approval.** Keeps the Tier B privacy promise.
- **Quarantine shows the reason, a short excerpt and an Info tip.** Makes the attack understandable (accepted trade-off: a small excerpt of attacker text is stored).
- **Release pre-fills from rules only.** Never trust the poisoned model output.
- **Redacted ledger lines on clear.** A balance between privacy and the audit trail.
- **Defence demo uses a rejection turned into an Offer.** The most visual harm; it shows on the dashboard.
- **Light theme only, inspired by Malwarebytes and Indeed.** Readability.

## What We're Building
Every page and behaviour under **Features and Behavior**, run on the synthetic inbox, with canary tests and recall/privacy numbers (`scope.md > The POC Boundary`).

## Deferred From the POC
- **Daily, weekly and bi-weekly scheduled scans:** these need a background service running while the app is closed, and are hard to show in a video. Scan-on-startup covers the need for now.
- **Real Gmail connection:** cut in scope. Excluded labels are modelled on Gmail labels so they carry over later.

## Possible Later Enhancements
- Scheduled background scans.
- Gmail read-only adapter, plus one-click access revocation.
- Managing the trusted-sender list (view, remove).

## Non-Goals
- Sending, replying to or modifying emails: read-only by design.
- Cloud sync, accounts, multi-user, mobile: contradict local-first.
- Dark mode: not needed for a simple, readability-first app.

## Open Questions
- **[Confirmed at review]** The scan summary wording and the tracker row fields listed above were filled in by Claude from your descriptions.
- **[Confirmed at review]** "Don't track this" matches on company + role.
- **[Confirmed at review]** The Privacy page holds the ledger, "everything we hold" and Delete all; Settings holds the defences toggle.
- **[Resolved in build]** A single segmented half-circle (learner choice at the early hands-on check).
