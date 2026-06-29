"""Timestamped output-directory creation, shared by every task."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def make_run_dir(data_dir: Path, label: str, session_started_at: datetime) -> Path:
    """Create and return ``data_dir/{label}_{YYYYMMDDTHHMMSS}``.

    *label* is the task-specific stem (e.g. ``"XXX000_run1"`` or
    ``"XXX000_example"``); the timestamp keeps repeated runs from colliding.
    """
    ts = session_started_at.strftime("%Y%m%dT%H%M%S")
    run_dir = data_dir / f"{label}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
