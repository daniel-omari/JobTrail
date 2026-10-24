"""`python -m jobtrail`: run startup tasks, start the app on 127.0.0.1, and open the browser."""
from __future__ import annotations

import threading
import webbrowser

import uvicorn

from .config import HOST
from .main import create_app
from .startup import run_startup_tasks


def main() -> None:
    app = create_app()
    print("JobTrail starting…")
    result = run_startup_tasks(app.state.config, app.state.source_factory, app.state.llm_factory)
    if result["auto_cleaned"]:
        print(f"  Auto-clean removed {result['auto_cleaned']} old archive entr{'y' if result['auto_cleaned'] == 1 else 'ies'}.")
    if result["scanned"]:
        s = result["summary"]
        print(f"  Startup scan: checked {s['checked']}, opened {s['opened']}, skipped {s['skipped']} unopened.")
    port = app.state.config.port
    url = f"http://{HOST}:{port}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"JobTrail running at {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
