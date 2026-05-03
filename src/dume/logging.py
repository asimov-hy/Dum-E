from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Return a project logger under the dume namespace."""

    if name.startswith("dume"):
        return logging.getLogger(name)
    return logging.getLogger(f"dume.{name}")


def setup_file_logging(log_dir: Path, filename: str = "dume.log") -> Path:
    """Create a file handler for DUM-E logs and return the log path."""

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / filename
    logger = get_logger("dume")
    logger.setLevel(logging.INFO)

    resolved_path = log_path.resolve()
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            if Path(handler.baseFilename).resolve() == resolved_path:
                return log_path

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return log_path
