"""`python -m jobtrail [--demo]`: run startup tasks, start the app on 127.0.0.1, and open the browser.

--demo  uses a separate, fresh data folder (backend/data-demo, wiped on each start) and shows the
        demo-only controls: the defences on/off toggle and "Reset scan data". Your normal data is untouched."""
from __future__ import annotations

import argparse
import shutil
import threading
import webbrowser

import uvicorn

from . import repo
from .config import DEFAULT_MODEL, DEMO_DATA_DIR, HOST, Config
from .db import connect
from .main import create_app
from .startup import run_startup_tasks
from .warmup import warm_up_in_background


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m jobtrail", description="JobTrail: local-first job application tracker")
    parser.add_argument("--demo", action="store_true", help="fresh demo data folder + demo-only controls")
    args = parser.parse_args()

    if args.demo:
        shutil.rmtree(DEMO_DATA_DIR, ignore_errors=True)  # demo data only: start every demo from a clean slate
        config = Config(data_dir=DEMO_DATA_DIR, demo=True)
    else:
        config = Config()
    app = create_app(config)
    print("JobTrail starting" + (" in DEMO mode (fresh demo data; your normal data is untouched)…" if args.demo else "…"))

    conn = connect(config.db_path)
    model = repo.get_settings(conn).get("model") or DEFAULT_MODEL
    conn.close()
    warm_up_in_background(config.ollama_url, model)

    result = run_startup_tasks(config, app.state.source_factory, app.state.llm_factory)
    if result["auto_cleaned"]:
        print(f"  Auto-clean removed {result['auto_cleaned']} old archive entr{'y' if result['auto_cleaned'] == 1 else 'ies'}.")
    if result["scanned"]:
        s = result["summary"]
        print(f"  Startup scan: checked {s['checked']}, opened {s['opened']}, skipped {s['skipped']} unopened.")
    url = f"http://{HOST}:{config.port}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"JobTrail running at {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host=HOST, port=config.port, log_level="warning")


if __name__ == "__main__":
    main()
