"""Load the local model into memory in the background at startup, so the first scan isn't slowed
by a ~30-second model load. Sends one tiny, email-free request; failures are ignored."""
from __future__ import annotations

import threading

from .pipeline.extract_llm import OllamaExtractor
from .sources.base import Header


def warm_up_in_background(base_url: str, model: str) -> threading.Thread:
    def run() -> None:
        llm = OllamaExtractor(base_url, model, timeout=180)
        try:
            if llm.available():
                from datetime import date
                h = Header(id="warmup", sender="warmup@localhost", display_name="", subject="warm-up", date=date.today())
                try:
                    llm.extract("warm-up", h)
                except Exception:  # noqa: BLE001 - a warm-up must never crash the app
                    pass
        finally:
            llm.close()

    t = threading.Thread(target=run, name="jobtrail-warmup", daemon=True)
    t.start()
    return t
