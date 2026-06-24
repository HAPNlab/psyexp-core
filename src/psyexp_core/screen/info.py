"""
Lean display enumeration: the :class:`ScreenInfo` record, the fast pyglet-only
screen list used by the picker, and index resolution. No OS-level enrichment
lives here — see :mod:`psyexp_core.screen.monitors` for that.
"""
from __future__ import annotations

from dataclasses import dataclass

import pyglet


@dataclass(frozen=True, slots=True)
class ScreenInfo:
    """One connected display, as pyglet reports it.

    ``index`` is the value PsychoPy/pyglet expect for ``visual.Window(screen=…)``
    and is what :func:`psyexp_core.screen.setup_screen` takes. ``x``/``y`` are the
    display's top-left position in the virtual desktop, which lets an operator tell
    side-by-side monitors apart when their resolutions match.
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
    (name, refresh rate, physical size, HiDPI scale) use
    :func:`psyexp_core.screen.query_monitors`.
    """
    screens = pyglet.canvas.get_display().get_screens()
    return [ScreenInfo(i, s.width, s.height, s.x, s.y) for i, s in enumerate(screens)]


def resolve_screen(screen: int | None) -> int:
    """Clamp a requested screen index to a currently-connected display.

    ``None`` (and any stale/out-of-range index — e.g. a monitor unplugged since
    the operator last chose it) resolves to the last display, preserving the
    historical "open on the last screen" default.
    """
    n = len(list_screens())
    if screen is None or not 0 <= screen < n:
        return n - 1
    return screen
