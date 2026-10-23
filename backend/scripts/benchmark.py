"""Recall / privacy / security benchmark on the synthetic inbox.

  python scripts/benchmark.py                 # rules-only mode (what CI runs)
  python scripts/benchmark.py --model qwen2.5:7b   # with the local AI (needs Ollama)

Numbers describe THIS synthetic inbox, which we wrote ourselves. They show the pipeline behaves as
designed; they are not a measure of real-world accuracy."""
from __future__ import annotations

import argparse
import glob
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtrail import repo  # noqa: E402
from jobtrail.config import OLLAMA_URL  # noqa: E402
from jobtrail.db import connect, init_db  # noqa: E402
from jobtrail.logging_setup import message_hash, setup_logging  # noqa: E402
from jobtrail.pipeline.extract_llm import OllamaExtractor  # noqa: E402
from jobtrail.pipeline.scan import run_scan  # noqa: E402
from jobtrail.sources.synthetic import SyntheticInbox  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "inbox.json"


def norm(s: str) -> str:
    return " ".join(s.lower().split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="Ollama model to use (default: rules only)")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db, log = Path(tmp) / "bench.db", Path(tmp) / "bench.log"
        init_db(db)
        logger = setup_logging(log)
        conn = connect(db)
        inbox = SyntheticInbox(FIXTURES)
        meta = inbox.meta()
        llm = None
        if args.model:
            llm = OllamaExtractor(OLLAMA_URL, args.model, timeout=120)
            if not llm.available():
                print(f"Model {args.model} not available in Ollama.")
                return 1
        summary = run_scan(conn, inbox, llm)

        by_hash = {message_hash(i): i for i in meta}
        stored = {by_hash[e["message_hash"]]: e["stored_summary"] for e in repo.ledger_list(conn)}
        review_subjects = {r["subject"] for r in repo.review_list(conn)}
        quarantined_subjects = {q["subject"] for q in repo.quarantine_list(conn)}
        headers = {h.id: h for h in inbox.list_headers()}

        hiring = [i for i, m in meta.items() if m["kind"] == "hiring"]
        tier_a = [i for i in hiring if meta[i]["decision"] == "open"]
        tier_b = [i for i in hiring if meta[i]["decision"] == "review"]
        correct = sum(
            1 for i in tier_a
            if stored.get(i) == f"company={meta[i]['company']}; role={meta[i]['role']}; status={meta[i]['status']}"
            or (stored.get(i, "").startswith("company=")
                and norm(stored[i]) == norm(f"company={meta[i]['company']}; role={meta[i]['role']}; status={meta[i]['status']}"))
        )
        to_review = sum(headers[i].subject in review_subjects for i in tier_b)
        caught = sum(i in stored for i in tier_a) + to_review
        personal = [i for i, m in meta.items() if m["kind"] == "personal"]
        noise = [i for i, m in meta.items() if m["kind"] == "noise"]
        malicious = [i for i, m in meta.items() if m["kind"] == "malicious"]
        conn.close()
        for handler in list(logger.handlers):  # release the log file (Windows can't delete open files)
            handler.close()
            logger.removeHandler(handler)
        blob = b"".join(open(p, "rb").read() for p in glob.glob(str(db) + "*") + [str(log)])
        canaries = [m["canary"] for m in meta.values() if m.get("canary")]
        leaked = [c for c in canaries if c.encode() in blob]
        false_quarantine = sum(headers[i].subject in quarantined_subjects for i in hiring)
        if llm:
            llm.close()

    mode = f"local AI ({args.model})" if args.model else "rules only"
    rows = [
        ("Hiring emails caught (tracked or sent to Review)", f"{caught} / {len(hiring)}"),
        ("Known-platform emails extracted fully correctly (company, role, status)", f"{correct} / {len(tier_a)}"),
        ("Tricky unknown-sender hiring emails sent to Review (unopened)", f"{to_review} / {len(tier_b)}"),
        ("Personal emails opened", f"{sum(i in inbox.body_reads for i in personal)} / {len(personal)}"),
        ("Job-alert / non-job 'application' emails opened", f"{sum(i in inbox.body_reads for i in noise)} / {len(noise)}"),
        ("Canary secrets found in database or log", f"{len(leaked)} / {len(canaries)}"),
        ("Prompt-injection emails quarantined", f"{sum(headers[i].subject in quarantined_subjects for i in malicious)} / {len(malicious)}"),
        ("Genuine hiring emails wrongly quarantined", f"{false_quarantine} / {len(hiring)}"),
    ]
    print(f"JobTrail benchmark, synthetic inbox ({len(meta)} emails), mode: {mode}\n")
    print("| Measure | Result |\n|---|---|")
    for k, v in rows:
        print(f"| {k} | {v} |")
    ok = not leaked and all(i not in inbox.body_reads for i in personal + noise) and false_quarantine == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
