"""
The ScreenDiagnostics dataclass, kept in its own import-light module (no PsychoPy
/ pyglet) so manifest writing and tests can use it without pulling in the GL
stack. ``screen.setup_screen`` populates it; ``manifest.write_manifest`` reads it.
"""
from __future__ import annotations

from dataclasses import dataclass


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
