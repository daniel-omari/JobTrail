"""`python -m jobtrail`: start the app on 127.0.0.1 and open the browser."""
from __future__ import annotations

import threading
import webbrowser

import uvicorn

from .config import HOST, PORT
from .main import create_app


def main() -> None:
    app = create_app()
    url = f"http://{HOST}:{PORT}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"JobTrail running at {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
