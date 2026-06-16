"""Keyboard helpers that work with either PTB or PsychoPy's event backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import psychtoolbox  # noqa: F401
except ImportError:
    KEYBOARD_BACKEND = "event"
else:
    KEYBOARD_BACKEND = "ptb"

from psychopy import event, prefs

if TYPE_CHECKING:
    from psychopy.hardware.keyboard import Keyboard


def configure_psychopy_backend() -> None:
    prefs.hardware["keyboardBackend"] = KEYBOARD_BACKEND
    if KEYBOARD_BACKEND != "ptb":
        warn_degraded_backend()


def warn_degraded_backend() -> None:
    """Loudly flag, at startup, that psychtoolbox is missing and the keyboard has
    fallen back to PsychoPy's ``event`` backend — which only captures keys while the
    PsychoPy window holds OS focus. Without this, the experimenter doesn't discover
    that keypresses (e.g. the start key) silently aren't registering until mid-run."""
    from rich.console import Console
    from rich.panel import Panel

    Console(stderr=True).print(
        Panel(
            "[bold]psychtoolbox is not installed[/bold] — the keyboard is using "
            "PsychoPy's\n[bold]event[/bold] backend, which only captures keypresses "
            "while the PsychoPy\nwindow has OS focus. If keys don't register "
            "mid-run, click the window\nfirst — or install psychtoolbox for the "
            "robust PTB backend.",
            title="[bold red]Keyboard: degraded backend[/bold red]",
            border_style="red",
            expand=False,
            padding=(1, 2),
        )
    )


def build_keyboard() -> Keyboard | None:
    if KEYBOARD_BACKEND == "ptb":
        from psychopy.hardware import keyboard

        kb = keyboard.Keyboard()
        # PsychoPy ≥2024.1 defaults muteOutsidePsychopy=True on macOS, silently
        # dropping keypresses when the PsychoPy window isn't the focused/registered
        # app (common when launched from a terminal or IDE). Disable it so keys are
        # accepted without first clicking the window to give it focus.
        try:
            kb.device.muteOutsidePsychopy = False
        except AttributeError:
            pass
        return kb
    return None


def clear_events(kb: Keyboard | None) -> None:
    if KEYBOARD_BACKEND == "ptb":
        if kb is not None:
            kb.clearEvents()
        return
    event.clearEvents(eventType="keyboard")


def wait_for_keys(kb: Keyboard | None, key_list: list[str]) -> list[str]:
    if KEYBOARD_BACKEND == "ptb":
        if kb is None:
            return []
        return [key_press.name for key_press in kb.waitKeys(keyList=key_list, waitRelease=False)]
    pressed = event.waitKeys(keyList=key_list)
    return [str(key_name) for key_name in (pressed or [])]


def get_keys(kb: Keyboard | None, key_list: list[str]) -> list[str]:
    if KEYBOARD_BACKEND == "ptb":
        if kb is None:
            return []
        return [key_press.name for key_press in kb.getKeys(keyList=key_list, waitRelease=False)]
    return [str(key_name) for key_name in event.getKeys(keyList=key_list)]
