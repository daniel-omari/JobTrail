"""Paths and defaults. Everything lives on this machine."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

HOST = "127.0.0.1"  # bind to loopback only: nothing else on the network can reach the app
PORT = 8000
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("JOBTRAIL_DATA_DIR", BACKEND_DIR / "data")))
    fixture_path: Path = BACKEND_DIR / "fixtures" / "inbox.json"
    frontend_dist: Path = REPO_DIR / "frontend" / "dist"
    ollama_url: str = OLLAMA_URL

    @property
    def db_path(self) -> Path:
        return self.data_dir / "jobtrail.db"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "jobtrail.log"
