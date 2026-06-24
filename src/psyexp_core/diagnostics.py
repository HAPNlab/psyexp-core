"""
The ScreenDiagnostics dataclass, kept in its own import-light module (no PsychoPy
/ pyglet) so manifest writing and tests can use it without pulling in the GL
stack. ``screen.setup_screen`` populates it; ``manifest.write_manifest`` reads it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScreenDiagnostics:
    gl_vendor: str
    gl_renderer: str
    win_type: str
    pyglet_version: str
    platform_str: str
    calib_median_ms: float
    calib_p99_ms: float
    calib_max_ms: float
    calib_n: int
    # OS-level detail for the display the task actually opened on (name, refresh
    # rate, physical size, HiDPI scale, …), as serialized by screen.query_monitors.
    # Kept as a plain dict so this module stays free of the pyglet/GL stack.
    monitor: dict[str, Any] | None = field(default=None)
