"""
Screen + frame-timing setup: enumerate the connected displays, open a fullscreen
PsychoPy window on a chosen one (defaulting to the last display), enable VSYNC,
run a short flip-interval calibration, and return the window alongside a
ScreenDiagnostics snapshot for the manifest.
"""
from __future__ import annotations

import platform
import statistics
from dataclasses import dataclass

import pyglet
from psychopy import core, monitors, visual

from psyexp_core.diagnostics import ScreenDiagnostics

__all__ = [
    "MonitorInfo",
    "ScreenDiagnostics",
    "ScreenInfo",
    "list_screens",
    "prompt_screen",
    "query_monitors",
    "setup_screen",
]


@dataclass(frozen=True, slots=True)
class ScreenInfo:
    """One connected display, as pyglet reports it.

    ``index`` is the value PsychoPy/pyglet expect for ``visual.Window(screen=…)``
    and is what :func:`setup_screen` takes. ``x``/``y`` are the display's top-left
    position in the virtual desktop, which lets an operator tell side-by-side
    monitors apart when their resolutions match.
    """

    index: int
    width: int
    height: int
    x: int
    y: int

    @property
    def label(self) -> str:
        return f"Display {self.index + 1}: {self.width}×{self.height} at ({self.x}, {self.y})"


def list_screens() -> list[ScreenInfo]:
    """Enumerate the connected displays in pyglet's screen order.

    This is the lean, fast enumeration used by the screen picker: resolution and
    virtual-desktop position only, straight from pyglet. For richer detail
    (name, refresh rate, physical size, HiDPI scale) use :func:`query_monitors`.
    """
    screens = pyglet.canvas.get_display().get_screens()
    return [ScreenInfo(i, s.width, s.height, s.x, s.y) for i, s in enumerate(screens)]


@dataclass(frozen=True, slots=True)
class MonitorInfo:
    """A display enriched with detail the OS knows but pyglet doesn't surface.

    Built on top of :class:`ScreenInfo` (same ``index`` and logical geometry),
    with extra fields filled in best-effort from platform APIs — Quartz on macOS,
    Win32/GDI on Windows. Every enriched field is ``None`` when the platform
    doesn't report it (e.g. ``refresh_hz`` is ``None`` on many built-in Mac panels
    that report a 0 Hz mode), so callers must treat them as optional.

    ``width_px``/``height_px`` are pyglet's *logical* size (points, pre-HiDPI
    scaling); multiply by ``scale_factor`` for backing pixels.
    """

    index: int
    width_px: int
    height_px: int
    x: int
    y: int
    name: str | None = None
    refresh_hz: float | None = None
    color_depth: int | None = None
    scale_factor: float | None = None
    physical_width_mm: float | None = None
    physical_height_mm: float | None = None
    is_primary: bool | None = None

    @property
    def diagonal_in(self) -> float | None:
        """Physical diagonal in inches, if the OS reported a physical size."""
        if self.physical_width_mm and self.physical_height_mm:
            import math

            return math.hypot(self.physical_width_mm, self.physical_height_mm) / 25.4
        return None

    @property
    def ppi(self) -> float | None:
        """Physical pixels per inch, if a physical size is known."""
        if not self.physical_width_mm:
            return None
        backing_px = self.width_px * (self.scale_factor or 1.0)
        return backing_px / (self.physical_width_mm / 25.4)

    def to_manifest(self) -> dict[str, object | None]:
        """A JSON-friendly snapshot of this display for the run manifest.

        Includes the derived ``diagonal_in``/``ppi`` so analysis doesn't have to
        recompute them; optional fields stay ``None`` when the OS didn't report
        them. ``position`` is the virtual-desktop origin.
        """
        diagonal = self.diagonal_in
        ppi = self.ppi
        return {
            "index": self.index,
            "name": self.name,
            "resolution": [self.width_px, self.height_px],
            "position": [self.x, self.y],
            "refresh_hz": self.refresh_hz,
            "color_depth": self.color_depth,
            "scale_factor": self.scale_factor,
            "physical_width_mm": self.physical_width_mm,
            "physical_height_mm": self.physical_height_mm,
            "diagonal_in": round(diagonal, 2) if diagonal is not None else None,
            "ppi": round(ppi, 1) if ppi is not None else None,
            "is_primary": self.is_primary,
        }


def query_monitors() -> list[MonitorInfo]:
    """Enumerate displays with OS-level detail (macOS and Windows only).

    Starts from pyglet's screen list (so ``index`` matches :func:`list_screens`
    and :func:`setup_screen`'s ``screen=``) and merges in per-display detail from
    the platform, matched by virtual-desktop position. On unsupported platforms,
    or when a platform call fails, the enriched fields are left ``None`` — the
    geometry from pyglet is always present.
    """
    screens = pyglet.canvas.get_display().get_screens()
    details = _platform_monitor_details()
    monitors_out: list[MonitorInfo] = []
    for i, s in enumerate(screens):
        fields = _pyglet_mode_fields(s)
        match = _match_detail(details, s.x, s.y, s.width, s.height)
        if match is not None:
            # Platform detail wins where present; keep pyglet's mode as fallback.
            # Skip the geometry keys — they're only used to match, and x/y/width
            # come from pyglet to stay consistent with list_screens/ScreenInfo.
            for key in fields:
                if match.get(key) is not None:
                    fields[key] = match[key]
        monitors_out.append(
            MonitorInfo(index=i, width_px=s.width, height_px=s.height, x=s.x, y=s.y, **fields)
        )
    return monitors_out


def _pyglet_mode_fields(screen) -> dict[str, object | None]:
    """Refresh rate / color depth from pyglet's current mode (cross-platform)."""
    fields: dict[str, object | None] = {
        "name": None,
        "refresh_hz": None,
        "color_depth": None,
        "scale_factor": None,
        "physical_width_mm": None,
        "physical_height_mm": None,
        "is_primary": None,
    }
    try:
        mode = screen.get_mode()
    except Exception:  # noqa: BLE001 — best-effort enrichment
        mode = None
    if mode is not None:
        if getattr(mode, "rate", 0):
            fields["refresh_hz"] = float(mode.rate)
        if getattr(mode, "depth", 0):
            fields["color_depth"] = int(mode.depth)
    return fields


def _match_detail(
    details: list[dict], x: int, y: int, width: int, height: int
) -> dict | None:
    """Match a pyglet screen to a platform-detail dict by position/geometry."""
    for detail in details:
        if detail.get("x") == x and detail.get("y") == y:
            return detail
    # Fall back to an exact size match if origins disagree (rare; coordinate-space
    # quirks between pyglet and the platform API).
    for detail in details:
        if detail.get("width") == width and detail.get("height") == height:
            return detail
    return None


def _platform_monitor_details() -> list[dict]:
    """Per-display detail from the OS. Empty list off macOS/Windows or on error."""
    import sys

    try:
        if sys.platform == "darwin":
            return _macos_monitor_details()
        if sys.platform == "win32":
            return _windows_monitor_details()
    except Exception:  # noqa: BLE001 — enrichment is optional; never break callers
        return []
    return []


def _macos_monitor_details() -> list[dict]:
    """Display detail via Quartz/CoreGraphics + AppKit (names)."""
    import Quartz
    from AppKit import NSScreen

    # Map CoreGraphics display id -> human-readable name (NSScreen, macOS 10.15+).
    names: dict[int, str] = {}
    for ns_screen in NSScreen.screens():
        number = ns_screen.deviceDescription().get("NSScreenNumber")
        if number is None:
            continue
        try:
            names[int(number)] = str(ns_screen.localizedName())
        except Exception:  # noqa: BLE001 — localizedName missing pre-10.15
            pass

    _err, display_ids, count = Quartz.CGGetActiveDisplayList(16, None, None)
    details: list[dict] = []
    for display_id in list(display_ids)[:count]:
        bounds = Quartz.CGDisplayBounds(display_id)
        physical = Quartz.CGDisplayScreenSize(display_id)  # millimetres
        mode = Quartz.CGDisplayCopyDisplayMode(display_id)
        refresh = Quartz.CGDisplayModeGetRefreshRate(mode) if mode else 0.0
        logical_w = Quartz.CGDisplayModeGetWidth(mode) if mode else 0
        pixel_w = Quartz.CGDisplayModeGetPixelWidth(mode) if mode else 0
        scale = (pixel_w / logical_w) if logical_w and pixel_w else None
        details.append(
            {
                "x": int(bounds.origin.x),
                "y": int(bounds.origin.y),
                "width": int(bounds.size.width),
                "height": int(bounds.size.height),
                "name": names.get(int(display_id)),
                "refresh_hz": float(refresh) or None,
                "color_depth": None,
                "scale_factor": scale,
                "physical_width_mm": float(physical.width) or None,
                "physical_height_mm": float(physical.height) or None,
                "is_primary": bool(Quartz.CGDisplayIsMain(display_id)),
            }
        )
    return details


def _windows_monitor_details() -> list[dict]:
    """Display detail via the Win32 GDI APIs (ctypes; no extra dependency)."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Per-monitor-DPI aware so positions/sizes aren't virtualized by the OS.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:  # noqa: BLE001 — already set, or pre-8.1
        pass

    class DISPLAY_DEVICEW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("DeviceName", wintypes.WCHAR * 32),
            ("DeviceString", wintypes.WCHAR * 128),
            ("StateFlags", wintypes.DWORD),
            ("DeviceID", wintypes.WCHAR * 128),
            ("DeviceKey", wintypes.WCHAR * 128),
        ]

    class POINTL(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wintypes.WCHAR * 32),
            ("dmSpecVersion", wintypes.WORD),
            ("dmDriverVersion", wintypes.WORD),
            ("dmSize", wintypes.WORD),
            ("dmDriverExtra", wintypes.WORD),
            ("dmFields", wintypes.DWORD),
            ("dmPosition", POINTL),
            ("dmDisplayOrientation", wintypes.DWORD),
            ("dmDisplayFixedOutput", wintypes.DWORD),
            ("dmColor", wintypes.SHORT),
            ("dmDuplex", wintypes.SHORT),
            ("dmYResolution", wintypes.SHORT),
            ("dmTTOption", wintypes.SHORT),
            ("dmCollate", wintypes.SHORT),
            ("dmFormName", wintypes.WCHAR * 32),
            ("dmLogPixels", wintypes.WORD),
            ("dmBitsPerPel", wintypes.DWORD),
            ("dmPelsWidth", wintypes.DWORD),
            ("dmPelsHeight", wintypes.DWORD),
            ("dmDisplayFlags", wintypes.DWORD),
            ("dmDisplayFrequency", wintypes.DWORD),
            ("dmICMMethod", wintypes.DWORD),
            ("dmICMIntent", wintypes.DWORD),
            ("dmMediaType", wintypes.DWORD),
            ("dmDitherType", wintypes.DWORD),
            ("dmReserved1", wintypes.DWORD),
            ("dmReserved2", wintypes.DWORD),
            ("dmPanningWidth", wintypes.DWORD),
            ("dmPanningHeight", wintypes.DWORD),
        ]

    ENUM_CURRENT_SETTINGS = -1
    DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001
    DISPLAY_DEVICE_PRIMARY_DEVICE = 0x00000004
    HORZSIZE, VERTSIZE = 4, 6  # GetDeviceCaps indices (millimetres)

    details: list[dict] = []
    adapter_index = 0
    while True:
        adapter = DISPLAY_DEVICEW()
        adapter.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if not user32.EnumDisplayDevicesW(None, adapter_index, ctypes.byref(adapter), 0):
            break
        adapter_index += 1
        if not adapter.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            continue

        devmode = DEVMODEW()
        devmode.dmSize = ctypes.sizeof(DEVMODEW)
        if not user32.EnumDisplaySettingsW(
            adapter.DeviceName, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode)
        ):
            continue

        # The attached monitor's friendly name (falls back to the adapter string).
        name = adapter.DeviceString
        monitor = DISPLAY_DEVICEW()
        monitor.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if user32.EnumDisplayDevicesW(adapter.DeviceName, 0, ctypes.byref(monitor), 0):
            name = monitor.DeviceString or name

        physical_w = physical_h = None
        hdc = gdi32.CreateDCW("DISPLAY", adapter.DeviceName, None, None)
        if hdc:
            physical_w = gdi32.GetDeviceCaps(hdc, HORZSIZE) or None
            physical_h = gdi32.GetDeviceCaps(hdc, VERTSIZE) or None
            gdi32.DeleteDC(hdc)

        scale = None
        try:
            point = POINTL(devmode.dmPosition.x + 1, devmode.dmPosition.y + 1)
            monitor_handle = user32.MonitorFromPoint(point, 2)  # NEAREST
            dpi_x, dpi_y = wintypes.UINT(), wintypes.UINT()
            if (
                ctypes.windll.shcore.GetDpiForMonitor(
                    monitor_handle, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
                )
                == 0
            ):
                scale = dpi_x.value / 96.0
        except Exception:  # noqa: BLE001 — DPI query is optional
            pass

        details.append(
            {
                "x": int(devmode.dmPosition.x),
                "y": int(devmode.dmPosition.y),
                "width": int(devmode.dmPelsWidth),
                "height": int(devmode.dmPelsHeight),
                "name": str(name) or None,
                "refresh_hz": float(devmode.dmDisplayFrequency) or None,
                "color_depth": int(devmode.dmBitsPerPel) or None,
                "scale_factor": scale,
                "physical_width_mm": float(physical_w) if physical_w else None,
                "physical_height_mm": float(physical_h) if physical_h else None,
                "is_primary": bool(adapter.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE),
            }
        )
    return details


def _resolve_screen(screen: int | None) -> int:
    """Clamp a requested screen index to a currently-connected display.

    ``None`` (and any stale/out-of-range index — e.g. a monitor unplugged since
    the operator last chose it) resolves to the last display, preserving the
    historical "open on the last screen" default.
    """
    n = len(list_screens())
    if screen is None or not 0 <= screen < n:
        return n - 1
    return screen


def prompt_screen(*, default: int | None = None) -> int:
    """Ask the operator which display to use; return the chosen screen index.

    The choice list is built from :func:`list_screens`. *default* pre-selects a
    screen (typically the one used last); an unset or stale *default* falls back
    to the last display. With a single display attached there is nothing to
    choose, so it returns ``0`` without prompting.
    """
    import questionary

    from psyexp_core import wizard  # local import: keeps screen.py importable headless

    screens = list_screens()
    if len(screens) <= 1:
        return 0
    default_index = _resolve_screen(default)
    # Only call the default "last used" when it's a real remembered choice; on a
    # first run *default* is None and _resolve_screen falls back to the last
    # display, which the operator never actually picked.
    remembered = default is not None and 0 <= default < len(screens)
    choices = [
        questionary.Choice(
            title=f"{s.label}  (last used)" if remembered and s.index == default_index
            else s.label,
            value=s.index,
        )
        for s in screens
    ]
    return wizard.ask_select(
        "Which display should the task run on?",
        choices,
        default=choices[default_index],
    )


def setup_screen(
    *,
    screen: int | None = None,
    color: tuple[float, float, float] = (-1, -1, -1),
    units: str = "height",
    warmup_flips: int = 30,
    calib_flips: int = 120,
) -> tuple[list[int], visual.Window, ScreenDiagnostics]:
    """Open a fullscreen window on *screen* and calibrate frame timing.

    *screen* is a display index from :func:`list_screens`; ``None`` (the default)
    or a stale index opens on the last display. Returns ``(win_res, win,
    diagnostics)``. The diagnostics carry GL/driver identifiers and a
    flip-interval calibration (median / p99 / max in ms) so timing spikes can be
    correlated with the compositor in post-hoc analysis.
    """
    screen = _resolve_screen(screen)
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
    intervals_ms.sort()
    median = statistics.median(intervals_ms)
    p99 = intervals_ms[int(0.99 * len(intervals_ms)) - 1]
    mx = intervals_ms[-1]

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
