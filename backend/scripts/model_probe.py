"""Compare local models on the synthetic inbox: extraction accuracy, speed, and whether the
demo attack fools them. Run:  python scripts/model_probe.py llama3.2:3b qwen2.5:7b"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobtrail.config import OLLAMA_URL  # noqa: E402
from jobtrail.pipeline.extract_llm import LlmError, OllamaExtractor  # noqa: E402
from jobtrail.pipeline.html_text import raw_text, split_text  # noqa: E402
from jobtrail.sources.synthetic import SyntheticInbox  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "inbox.json"


def norm(s: str) -> str:
    return " ".join(s.lower().split())


def probe(model: str) -> None:
    inbox = SyntheticInbox(FIXTURES)
    meta = inbox.meta()
    headers = {h.id: h for h in inbox.list_headers()}
    llm = OllamaExtractor(OLLAMA_URL, model, timeout=120)
    if not llm.available():
        print(f"{model}: not available in Ollama")
        return
    llm.extract("warm-up", next(iter(headers.values())))  # load model into memory

    full = status_ok = invalid = 0
    misses, times = [], []
    hiring = [i for i, m in meta.items() if m["kind"] == "hiring" and m["decision"] == "open"]
    for mid in hiring:
        m, h = meta[mid], headers[mid]
        visible, _ = split_text(inbox._read_body(mid))
        t = time.perf_counter()
        try:
            ex = llm.extract(visible, h)
        except LlmError:
            invalid += 1
            misses.append(f"{mid}: invalid output")
            continue
        finally:
            times.append(time.perf_counter() - t)
        ok_status = ex.status.value == m["status"]
        status_ok += ok_status
        if ok_status and norm(ex.company) == norm(m["company"]) and norm(ex.role) == norm(m["role"]):
            full += 1
        else:
            misses.append(f"{mid}: got {ex.company!r} / {ex.role!r} / {ex.status.value}  expected {m['company']!r} / {m['role']!r} / {m['status']}")

    print(f"\n=== {model} ===")
    print(f"Extraction (guarded prompt, {len(hiring)} hiring emails): all three fields right {full}/{len(hiring)}, "
          f"status right {status_ok}/{len(hiring)}, invalid {invalid}")
    print(f"Average time per email: {sum(times) / len(times):.2f}s")
    for line in misses:
        print("   miss", line)

    print("Attack emails (no detector, no cross-check):")
    for mid in ("m01", "m02", "m04"):
        h, m = headers[mid], meta[mid]
        body = inbox._read_body(mid)
        visible, _ = split_text(body)
        results = []
        for label, fn, text in (("naive+raw", llm.extract_naive, raw_text(body)),
                                ("guarded+raw", llm.extract, raw_text(body)),
                                ("guarded+visible", llm.extract, visible)):
            try:
                results.append(f"{label}={fn(text, h).status.value}")
            except LlmError:
                results.append(f"{label}=INVALID")
        print(f"   {mid} ({m['attack']}, truly {m['status']}): " + "  ".join(results))
    llm.close()


if __name__ == "__main__":
    for model in sys.argv[1:] or ["llama3.2:3b"]:
        probe(model)
