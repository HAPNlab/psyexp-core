"""Tests for write_manifest and system_info (PsychoPy-free)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from psyexp_core import __version__
from psyexp_core.manifest import system_info, write_manifest


@dataclass
class _FakeScreenDiag:
    gl_vendor: str = "TestVendor"
    gl_renderer: str = "TestRenderer"
    win_type: str = "pyglet"
    pyglet_version: str = "2.0"
    platform_str: str = "test"
    calib_median_ms: float = 16.7
    calib_p99_ms: float = 17.0
    calib_max_ms: float = 18.0
    calib_n: int = 120
    monitor: dict | None = None


def test_system_info_keys():
    info = system_info()
    for key in (
        "hostname", "platform", "machine", "processor",
        "os_name", "os_release", "python_version", "psychopy_version", "git_commit",
    ):
        assert key in info


def test_write_manifest_full(tmp_path: Path):
    out = write_manifest(
        tmp_path,
        header={"medoc_version": "0.1.0", "subject_id": "S1", "run_file": "example.toml"},
        session_time=datetime(2026, 6, 9, 14, 30, 0),
        screen_diag=_FakeScreenDiag(),
        win_res=[1920, 1080],
        study_params={"baseline": 35.0, "target_temp": 47.0},
        frame_rate=60.0,
        n_trials=6,
        frame_dur_s=0.0167,
        frame_dur_source="calibration",
    )
    assert out == tmp_path / "manifest.json"
    m = json.loads(out.read_text())

    # core-owned fields
    assert m["psyexp_core_version"] == __version__
    assert "system" in m and "psychopy_version" in m["system"]
    assert m["process"]["argv"]  # argv recorded

    # header merged verbatim
    assert m["medoc_version"] == "0.1.0"
    assert m["subject_id"] == "S1"
    assert m["run_file"] == "example.toml"

    # session / study fields
    assert m["session_time"] == "2026-06-09T14:30:00"
    assert m["frame_rate_hz"] == 60.0
    assert m["n_trials"] == 6
    assert m["study_params"]["target_temp"] == 47.0

    # display block + vsync calibration
    assert m["display"]["resolution"] == [1920, 1080]
    assert m["display"]["gl_renderer"] == "TestRenderer"
    assert m["display"]["frame_dur_ms"] == round(0.0167 * 1000, 4)
    assert m["display"]["frame_dur_source"] == "calibration"
    assert m["display"]["vsync_calibration"]["n_samples"] == 120


def test_write_manifest_minimal_omits_optional_blocks(tmp_path: Path):
    out = write_manifest(
        tmp_path,
        header={"subject_id": "S1"},
        session_time=datetime(2026, 6, 9, 14, 30, 0),
    )
    m = json.loads(out.read_text())
    assert m["subject_id"] == "S1"
    assert "display" not in m       # no screen_diag passed
    assert "study_params" not in m  # not supplied
    assert "frame_rate_hz" not in m
    assert "system" in m            # always present
