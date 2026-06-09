"""
Run manifest (manifest.json) writing plus the best-effort system/hardware
diagnostics it embeds. ``write_manifest`` is task-agnostic: the task supplies its
own top-level fields via *header* and its parameters via *study_params*; the
system / display / process blocks and the resolved psyexp-core version are
filled in here so every task records the same reproducibility metadata.
"""
from __future__ import annotations

import json
import platform
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psyexp_core.diagnostics import ScreenDiagnostics

__all__ = ["system_info", "write_manifest"]


def _git_commit() -> str:
    """Short HEAD of the *caller's* working directory (i.e. the task repo)."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:  # noqa: BLE001 — diagnostic only
        return "unknown"


def _cpu_name() -> str:
    """Best-effort friendly CPU name.

    ``platform.processor()`` returns the raw CPUID descriptor on Windows
    (e.g. "Intel64 Family 6 Model 158 Stepping 11") and the bare arch on
    macOS, neither of which is a marketing name. Read the registry on
    Windows; otherwise fall back to ``platform.processor()``.
    """
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            try:
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            finally:
                winreg.CloseKey(key)
            if name:
                return str(name).strip()
        except Exception:  # noqa: BLE001 — diagnostic only
            pass
    return platform.processor() or "unknown"


def _psychopy_version() -> str:
    try:
        import psychopy  # type: ignore

        return getattr(psychopy, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def system_info() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": _cpu_name(),
        "os_name": platform.system(),
        "os_release": platform.release(),
        "python_version": platform.python_version(),
        "psychopy_version": _psychopy_version(),
        "git_commit": _git_commit(),
    }


def write_manifest(
    run_dir: Path,
    *,
    header: dict[str, Any],
    session_time: datetime,
    screen_diag: ScreenDiagnostics | None = None,
    win_res: list[int] | None = None,
    study_params: dict[str, Any] | None = None,
    frame_rate: float | None = None,
    n_trials: int | None = None,
    frame_dur_s: float | None = None,
    frame_dur_source: str | None = None,
    extra_process: dict[str, Any] | None = None,
) -> Path:
    """Write ``run_dir/manifest.json`` and return its path.

    *header* carries the task's own top-level fields (subject_id, run, plus the
    task's own version key, e.g. ``{"medoc_version": ...}``) and is merged in
    verbatim. *study_params* is the task's parameter block. The ``system`` /
    ``display`` / ``process`` blocks and ``psyexp_core_version`` are added here.
    """
    from psyexp_core import __version__

    manifest: dict[str, Any] = {"psyexp_core_version": __version__}
    manifest.update(header)
    manifest["session_time"] = session_time.isoformat(timespec="seconds")
    if frame_rate is not None:
        manifest["frame_rate_hz"] = round(frame_rate, 3)
    if n_trials is not None:
        manifest["n_trials"] = n_trials
    if study_params is not None:
        manifest["study_params"] = study_params

    manifest["system"] = system_info()

    if screen_diag is not None:
        display: dict[str, Any] = {
            "gl_vendor": screen_diag.gl_vendor,
            "gl_renderer": screen_diag.gl_renderer,
            "win_type": screen_diag.win_type,
            "pyglet_version": screen_diag.pyglet_version,
            "resolution": [int(x) for x in win_res] if win_res is not None else None,
            "vsync_calibration": {
                "median_ms": screen_diag.calib_median_ms,
                "p99_ms": screen_diag.calib_p99_ms,
                "max_ms": screen_diag.calib_max_ms,
                "n_samples": screen_diag.calib_n,
            },
        }
        if frame_dur_s is not None:
            display["frame_dur_ms"] = round(frame_dur_s * 1000, 4)
        if frame_dur_source is not None:
            display["frame_dur_source"] = frame_dur_source
        manifest["display"] = display

    process: dict[str, Any] = {"argv": sys.argv}
    if extra_process:
        process.update(extra_process)
    manifest["process"] = process

    path = run_dir / "manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return path
