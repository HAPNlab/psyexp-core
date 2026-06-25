"""
Window setup and frame-timing calibration: open a fullscreen PsychoPy window on
a chosen display, enable VSYNC, run a short flip-interval calibration, and return
the window alongside a :class:`ScreenDiagnostics` snapshot for the manifest.
"""
from __future__ import annotations

import platform

import numpy as np
import pyglet
from psychopy import core, monitors, visual

from psyexp_core.diagnostics import ScreenDiagnostics
from psyexp_core.screen.info import resolve_screen
from psyexp_core.screen.monitors import query_monitors


def setup_screen(
    *,
    screen: int | None = None,
    color: tuple[float, float, float] = (-1, -1, -1),
    units: str = "height",
    warmup_flips: int = 30,
    calib_flips: int = 120,
) -> tuple[list[int], visual.Window, ScreenDiagnostics]:
    """Open a fullscreen window on *screen* and calibrate frame timing.

    *screen* is a display index from :func:`psyexp_core.screen.list_screens`;
    ``None`` (the default) or a stale index opens on the last display. Returns
    ``(win_res, win, diagnostics)``. The diagnostics carry GL/driver identifiers
    and a flip-interval calibration (median / p99 / max in ms) so timing spikes
    can be correlated with the compositor in post-hoc analysis.
    """
    screen = resolve_screen(screen)
    screens = pyglet.canvas.get_display().get_screens()
    win_res = [screens[screen].width, screens[screen].height]

    # Snapshot OS-level detail for the display we're about to open on, so the
    # manifest records which physical monitor the task actually ran on.
    monitor_detail: dict[str, object | None] | None = None
    try:
        monitors_info = query_monitors()
        if 0 <= screen < len(monitors_info):
            monitor_detail = monitors_info[screen].to_manifest()
    except Exception:  # noqa: BLE001 — enrichment is optional; never break setup
        monitor_detail = None

    exp_mon = monitors.Monitor("exp_mon")
    exp_mon.setSizePix(win_res)
    win = visual.Window(
        size=win_res,
        screen=screen,
        allowGUI=True,
        fullscr=True,
        monitor=exp_mon,
        units=units,
        color=color,
        waitBlanking=True,
    )

    # Explicitly enable VSYNC on the pyglet window.
    handle = getattr(win, "winHandle", None)
    if handle is not None and hasattr(handle, "set_vsync"):
        handle.set_vsync(True)

    # Collect backend identifiers so timing spikes can be correlated with
    # driver/compositor in post-hoc analysis.
    try:
        gl_info = pyglet.gl.current_context.get_info()
        gl_vendor = gl_info.get_vendor()
        gl_renderer = gl_info.get_renderer()
    except Exception:  # noqa: BLE001 — diagnostic only
        gl_vendor = "?"
        gl_renderer = "?"

    # VSYNC calibration: flip ~120 times and measure intervals. If the 99th
    # percentile is well above one frame period, vsync is not actually blocking
    # — typical on Windows under DWM composition or borderless fullscreen.
    intervals_ms: list[float] = []
    # Warm-up flips before measurement: PsychoPy's detectingFrameDrops doc notes
    # drops are common during startup as the GPU/driver/compositor settle. Run
    # these before the calibration loop so the median feeding frame_dur_s is
    # measured on a settled context, not a cold one.
    for _ in range(warmup_flips):
        win.flip()
    last_t = core.getTime()
    for _ in range(calib_flips):
        win.flip()
        now = core.getTime()
        intervals_ms.append((now - last_t) * 1000)
        last_t = now
    arr = np.asarray(intervals_ms)
    median = float(np.median(arr))
    p99 = float(np.percentile(arr, 99))
    mx = float(arr.max())

    # Enable PsychoPy's frame interval recording so callers can read
    # win.nDroppedFrames and isolate on-screen drops from measurement artifacts.
    win.refreshThreshold = (median / 1000.0) * 1.5
    win.recordFrameIntervals = True

    diagnostics = ScreenDiagnostics(
        gl_vendor=gl_vendor,
        gl_renderer=gl_renderer,
        win_type=str(getattr(win, "winType", "?")),
        pyglet_version=str(getattr(pyglet, "version", "?")),
        platform_str=platform.platform(),
        calib_median_ms=round(median, 3),
        calib_p99_ms=round(p99, 3),
        calib_max_ms=round(mx, 3),
        calib_n=len(intervals_ms),
        monitor=monitor_detail,
    )

    return win_res, win, diagnostics
