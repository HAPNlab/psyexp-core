"""
The interactive screen picker: ask the operator which display to run on, built
from the lean :func:`psyexp_core.screen.list_screens` enumeration.
"""
from __future__ import annotations

from psyexp_core.screen.info import list_screens, resolve_screen


def prompt_screen(*, default: int | None = None) -> int:
    """Ask the operator which display to use; return the chosen screen index.

    The choice list is built from :func:`psyexp_core.screen.list_screens`.
    *default* pre-selects a screen (typically the one used last); an unset or stale
    *default* falls back to the last display. With a single display attached there
    is nothing to choose, so it returns ``0`` without prompting.
    """
    import questionary

    from psyexp_core import wizard  # local import: keeps screen importable headless

    screens = list_screens()
    if len(screens) <= 1:
        return 0
    default_index = resolve_screen(default)
    # Only call the default "last used" when it's a real remembered choice; on a
    # first run *default* is None and resolve_screen falls back to the last
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
