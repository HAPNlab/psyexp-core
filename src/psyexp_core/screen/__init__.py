"""
Screen + frame-timing setup: enumerate the connected displays, open a fullscreen
PsychoPy window on a chosen one (defaulting to the last display), enable VSYNC,
run a short flip-interval calibration, and return the window alongside a
ScreenDiagnostics snapshot for the manifest.

Split across submodules by concern (this package imports PsychoPy regardless,
just like the old single module did):

- :mod:`~psyexp_core.screen.info` — lean pyglet-only enumeration (``ScreenInfo``,
  ``list_screens``); no GL, no OS probes.
- :mod:`~psyexp_core.screen.monitors` / :mod:`~psyexp_core.screen.platform_detail`
  — displays enriched with OS-level detail (``MonitorInfo``, ``query_monitors``).
- :mod:`~psyexp_core.screen.picker` — the interactive operator screen picker.
- :mod:`~psyexp_core.screen.setup` — opens the window and calibrates frame timing.

Import this package and use the names below; the submodule layout is an internal
detail.
"""
from __future__ import annotations

from psyexp_core.diagnostics import ScreenDiagnostics
from psyexp_core.screen.info import ScreenInfo, list_screens
from psyexp_core.screen.monitors import MonitorInfo, query_monitors
from psyexp_core.screen.picker import prompt_screen
from psyexp_core.screen.setup import setup_screen

__all__ = [
    "MonitorInfo",
    "ScreenDiagnostics",
    "ScreenInfo",
    "list_screens",
    "prompt_screen",
    "query_monitors",
    "setup_screen",
]
