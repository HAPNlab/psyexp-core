"""
Per-display detail straight from the OS, returned as plain dicts keyed by
virtual-desktop geometry so :mod:`psyexp_core.screen.monitors` can match them
against pyglet's screen list. Quartz/CoreGraphics + AppKit on macOS, Win32 GDI
(via ctypes) on Windows. Every probe is best-effort: it returns ``[]`` rather
than raising on unsupported platforms or API failures.
"""
from __future__ import annotations


def platform_monitor_details() -> list[dict]:
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

    # PyObjC populates AppKit dynamically, so static analyzers can't see NSScreen.
    # noinspection PyUnresolvedReferences
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
