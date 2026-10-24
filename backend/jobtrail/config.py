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
DEFAULT_MODEL = "qwen2.5:7b"  # chosen by the learner after scripts/model_probe.py (17/17 extraction, 0.24s/email)


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("JOBTRAIL_DATA_DIR", BACKEND_DIR / "data")))
    fixture_path: Path = BACKEND_DIR / "fixtures" / "inbox.json"
    frontend_dist: Path = REPO_DIR / "frontend" / "dist"
    ollama_url: str = OLLAMA_URL
    port: int = field(default_factory=lambda: int(os.environ.get("JOBTRAIL_PORT", PORT)))
    extra_hosts: tuple[str, ...] = ()  # e.g. the test client's host

    @property
    def allowed_hosts(self) -> set[str]:
        """Host headers we answer. Anything else (e.g. a DNS-rebinding attacker's domain) is refused."""
        ports = {self.port, 5173}  # 5173 = Vite dev server proxy (development only)
        return {f"{h}:{p}" for h in ("127.0.0.1", "localhost") for p in ports} | set(self.extra_hosts)

    @property
    def allowed_origins(self) -> set[str]:
        return {f"http://{h}" for h in self.allowed_hosts}

    @property
    def db_path(self) -> Path:
        return self.data_dir / "jobtrail.db"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "jobtrail.log"
