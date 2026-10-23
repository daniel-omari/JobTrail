"""App log. By design it only ever records event types and message-id hashes,
never senders, subjects or bodies. The canary test reads this file to prove it."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

LOGGER_NAME = "jobtrail"


def message_hash(message_id: str) -> str:
    return hashlib.sha256(message_id.encode("utf-8")).hexdigest()


def short_hash(message_id: str) -> str:
    return message_hash(message_id)[:10]


def setup_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
