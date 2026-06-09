"""
Reusable building blocks for terminal setup wizards: a shared questionary /
prompt_toolkit colour palette, thin ``ask_*`` helpers that apply the palette and
treat Ctrl-C / Esc as "quit the task", a positive-float validator, and a
filename prompt that guards against clobbering an existing file. Tasks compose
their own wizard from these; task-specific fields (e.g. a frame-stepping RT
prompt) stay in the task repo.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NoReturn

import questionary
from prompt_toolkit import prompt as _pt_prompt
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.styles import Style as PtStyle
from prompt_toolkit.validation import ValidationError, Validator
from rich.console import Console

_rcon = Console(stderr=True)

# ── Styles ──────────────────────────────────────────────────────────────────

# Match questionary's default palette so everything looks cohesive.
QSTYLE = questionary.Style(
    [
        ("qmark", "fg:#5f819d bold"),
        ("question", "bold"),
        ("answer", "fg:#ff9d00 bold"),
        ("pointer", "fg:#ff9d00 bold"),
        ("highlighted", "fg:#ff9d00 bold"),
        ("selected", "fg:#cc5454"),
        ("separator", "fg:#6c6c6c"),
        ("instruction", "fg:#858585 italic"),
        ("placeholder", "fg:#6c6c6c"),
    ]
)

# prompt_toolkit style for the custom prompts.
PT_STYLE = PtStyle.from_dict(
    {
        "prompt": "#ff9d00 bold",           # ❯ arrow: matches questionary answer
        "placeholder": "#6c6c6c italic",    # greyed-out example, not submitted
        "bottom-toolbar": "bg:#1e1e1e #888888",
        "bottom-toolbar.text": "bg:#1e1e1e",
    }
)


# ── Quit / cancel ─────────────────────────────────────────────────────────────


def quit_app() -> NoReturn:
    """Quit PsychoPy + the process. Called when an operator cancels a prompt."""
    from psychopy import core  # late import — avoids slow startup / circulars

    core.quit()
    raise SystemExit(0)  # unreachable; tells the type checker this never returns


# ── Thin questionary helpers (apply QSTYLE; cancel ⇒ quit_app) ─────────────────


def ask_text(
    message: str,
    *,
    placeholder: str | None = None,
    default: str = "",
    validate: Callable[[str], bool | str] | None = None,
) -> str:
    ph = HTML(f"<placeholder>{placeholder}</placeholder>") if placeholder else None
    answer = questionary.text(
        message,
        default=default,
        placeholder=ph,
        validate=validate,
        style=QSTYLE,
    ).ask()
    if answer is None:
        quit_app()
    return answer


def ask_select(message: str, choices: Sequence[questionary.Choice | str]):
    answer = questionary.select(message, choices=list(choices), style=QSTYLE).ask()
    if answer is None:
        quit_app()
    return answer


def ask_confirm(message: str, *, default: bool = True) -> bool:
    answer = questionary.confirm(message, default=default, style=QSTYLE).ask()
    if answer is None:
        quit_app()
    return answer


# ── Validators ────────────────────────────────────────────────────────────────


class PosFloatValidator(Validator):
    """prompt_toolkit validator: text must parse to a float > 0."""

    def __init__(self, unit: str = "") -> None:
        self._suffix = f" ({unit})" if unit else ""

    def validate(self, document) -> None:
        text = document.text.strip()
        try:
            value = float(text)
        except ValueError:
            raise ValidationError(
                message=f"Enter a number{self._suffix}", cursor_position=len(text)
            ) from None
        if value <= 0:
            raise ValidationError(
                message=f"Value must be > 0{self._suffix}", cursor_position=len(text)
            )


# ── Filename prompt with overwrite guard ──────────────────────────────────────


def prompt_unique_name(
    label: str,
    target_dir: Path,
    filename_for: Callable[[str], str],
    *,
    example: str = "1",
) -> str:
    """Prompt for a NAME and guard against clobbering an existing file.

    *filename_for* maps the entered NAME to the target filename inside
    *target_dir*. Re-prompts until the resulting path is free or the operator
    confirms an overwrite, then returns the chosen NAME.
    """
    _rcon.print(
        f"[bold #5f819d]?[/bold #5f819d] [bold]{label}[/bold]  "
        "[dim]NAME is only part of the saved file[/dim]",
        highlight=False,
    )

    def _toolbar() -> FormattedText:
        typed = get_app().current_buffer.text.strip()
        if not typed:
            return FormattedText([("fg:ansired bold", " ✗  Name cannot be empty")])
        preview = target_dir / filename_for(typed)
        return FormattedText([("fg:ansigreen bold", f" → saves as {preview}")])

    while True:
        try:
            raw = _pt_prompt(
                FormattedText([("class:prompt", "❯ ")]),
                placeholder=HTML(f"<placeholder>e.g. {example}</placeholder>"),
                bottom_toolbar=_toolbar,
                style=PT_STYLE,
            )
        except (KeyboardInterrupt, EOFError):
            quit_app()
        name = raw.strip()
        if not name:
            _rcon.print("[red]Name cannot be empty.[/red]")
            continue

        target = target_dir / filename_for(name)
        if not target.exists():
            return name

        if ask_confirm(
            f"{target.name} already exists in {target_dir}/ — overwrite?",
            default=False,
        ):
            return name
        # else: loop and re-prompt for a different NAME
