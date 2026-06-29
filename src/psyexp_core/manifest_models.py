"""
Pydantic models for the structured blocks of ``manifest.json``.

These type the parts of the manifest that psyexp-core owns and fully controls —
the ``system`` / ``display`` / ``vsync_calibration`` blocks — and let
``model_dump(exclude_none=True)`` handle the optional-field pruning that
``write_manifest`` used to do by hand. The top-level :class:`Manifest` stays
partly open (``extra="allow"``) because each task merges its own ``header`` fields
in verbatim and supplies an arbitrary ``study_params`` block.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SystemInfo(BaseModel):
    """The ``system`` block — see :func:`psyexp_core.manifest.system_info`."""

    hostname: str
    platform: str
    machine: str
    processor: str
    os_name: str
    os_release: str
    python_version: str
    psychopy_version: str
    git_commit: str


class VsyncCalibration(BaseModel):
    """Flip-interval calibration summary (all in ms except ``n_samples``)."""

    median_ms: float
    p99_ms: float
    max_ms: float
    n_samples: int


class Display(BaseModel):
    """The ``display`` block: backend identifiers + timing calibration."""

    gl_vendor: str
    gl_renderer: str
    win_type: str
    pyglet_version: str
    resolution: list[int] | None = None
    vsync_calibration: VsyncCalibration
    frame_dur_ms: float | None = None
    frame_dur_source: str | None = None
    monitor: dict[str, Any] | None = None


class Manifest(BaseModel):
    """Top-level manifest wrapper.

    The task's ``header`` fields are merged in verbatim as extra attributes, so
    ``extra="allow"`` keeps them; ``study_params`` is arbitrary per task.
    """

    model_config = ConfigDict(extra="allow")

    psyexp_core_version: str
    session_started_at: str
    frame_rate_hz: float | None = None
    n_trials: int | None = None
    study_params: dict[str, Any] | None = None
    system: SystemInfo
    display: Display | None = None
    process: dict[str, Any]
