"""
Displays enriched with OS-level detail: the :class:`MonitorInfo` record and
:func:`query_monitors`, which starts from pyglet's screen list and merges in the
platform probes from :mod:`psyexp_core.screen.platform_detail`. ``MonitorInfo``
also knows how to serialize itself for the run manifest.
"""
from __future__ import annotations

from dataclasses import dataclass

import pyglet

from psyexp_core.screen.platform_detail import platform_monitor_details


@dataclass(frozen=True, slots=True)
class MonitorInfo:
    """A display enriched with detail the OS knows but pyglet doesn't surface.

    Built on top of :class:`psyexp_core.screen.ScreenInfo` (same ``index`` and
    logical geometry), with extra fields filled in best-effort from platform APIs
    — Quartz on macOS, Win32/GDI on Windows. Every enriched field is ``None`` when
    the platform doesn't report it (e.g. ``refresh_hz`` is ``None`` on many
    built-in Mac panels that report a 0 Hz mode), so callers must treat them as
    optional.

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

    Starts from pyglet's screen list (so ``index`` matches
    :func:`psyexp_core.screen.list_screens` and ``setup_screen``'s ``screen=``)
    and merges in per-display detail from the platform, matched by virtual-desktop
    position. On unsupported platforms, or when a platform call fails, the enriched
    fields are left ``None`` — the geometry from pyglet is always present.
    """
    screens = pyglet.canvas.get_display().get_screens()
    details = platform_monitor_details()
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
