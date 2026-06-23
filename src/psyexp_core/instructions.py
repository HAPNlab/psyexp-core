"""
A self-paced, keypress-driven instruction pager. The task supplies the pages and
a *draw_page* callback that renders one page (the task owns its stimuli and
layout); this module owns the navigation loop — forward / optional back / quit —
and the flip + key polling, reusing the shared keyboard abstraction.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, TypeVar

from psyexp_core.keyboard import clear_events, get_keys

if TYPE_CHECKING:
    from psychopy import visual
    from psychopy.hardware.keyboard import Keyboard

_Page = TypeVar("_Page")


def _default_quit() -> None:
    from psychopy import core

    core.quit()


def page_through(
    win: visual.Window,
    pages: Sequence[_Page],
    draw_page: Callable[[_Page, bool], None],
    *,
    forward_keys: Sequence[str],
    back_keys: Sequence[str] = (),
    quit_keys: Sequence[str] = (),
    kb: Keyboard | None = None,
    on_quit: Callable[[], None] | None = None,
) -> None:
    """Page through *pages* one at a time until the operator advances past the last.

    *draw_page(page, is_last)* draws (but does not flip) a single page. Forward
    keys advance — and return once past the last page; back keys step back (no-op
    on the first page); quit keys call *on_quit* (defaults to ``psychopy.core.quit``).
    """
    if not pages:
        return

    quit_fn = on_quit or _default_quit
    keys = [*forward_keys, *back_keys, *quit_keys]

    clear_events(kb)
    page_idx = 0
    while True:
        # Poll (rather than block on waitKeys) so the window keeps flipping each
        # frame; on macOS a window that flips once and then blocks may never come
        # to the foreground to receive keypresses.
        draw_page(pages[page_idx], page_idx == len(pages) - 1)
        win.flip()

        pressed = get_keys(kb, keys)
        if not pressed:
            continue
        key_name = pressed[0]
        if key_name in quit_keys:
            quit_fn()
        elif key_name in back_keys and page_idx > 0:
            page_idx -= 1
        elif key_name in forward_keys:
            if page_idx == len(pages) - 1:
                return
            page_idx += 1
