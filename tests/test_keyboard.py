"""Tests for the timed-press + keyboard-clock helpers.

These read a Keyboard object directly, so they're exercised with a small fake
keyboard / window that mimics PsychoPy's getKeys / callOnFlip / clock surface.
"""
from __future__ import annotations

import psyexp_core.keyboard as kbd
from psyexp_core.keyboard import (
    KeyPress,
    check_quit,
    clock_time,
    get_presses,
    reset_clock,
    reset_clock_on_flip,
    wait_for_key,
)


class _FakeClock:
    def __init__(self) -> None:
        self._t = 0.0

    def set(self, t: float) -> None:
        self._t = t

    def reset(self) -> None:
        self._t = 0.0

    def getTime(self) -> float:
        return self._t


class _FakeKeyPress:
    def __init__(self, name: str, rt: float) -> None:
        self.name = name
        self.rt = rt


class _FakeKeyboard:
    def __init__(self) -> None:
        self.clock = _FakeClock()
        self._queued: list[_FakeKeyPress] = []

    def queue(self, name: str, rt: float) -> None:
        self._queued.append(_FakeKeyPress(name, rt))

    def getKeys(self, keyList=None, waitRelease=True):
        out = [p for p in self._queued if keyList is None or p.name in keyList]
        self._queued = [p for p in self._queued if p not in out]
        return out


class _FakeWindow:
    def __init__(self) -> None:
        self._cbs: list = []

    def callOnFlip(self, fn, *args, **kwargs) -> None:
        self._cbs.append((fn, args, kwargs))

    def flip(self) -> None:
        cbs, self._cbs = self._cbs, []
        for fn, args, kwargs in cbs:
            fn(*args, **kwargs)


def test_get_presses_maps_name_and_rt():
    kb = _FakeKeyboard()
    kb.queue("1", 0.234)
    kb.queue("2", 0.512)
    presses = get_presses(kb, ["1", "2"])
    assert presses == [KeyPress("1", 0.234), KeyPress("2", 0.512)]


def test_get_presses_filters_by_key_list():
    kb = _FakeKeyboard()
    kb.queue("1", 0.1)
    kb.queue("escape", 0.2)
    presses = get_presses(kb, ["1"])
    assert [p.name for p in presses] == ["1"]


def test_get_presses_none_kb_returns_empty():
    assert get_presses(None, ["1"]) == []


def test_reset_clock_and_clock_time():
    kb = _FakeKeyboard()
    kb.clock.set(5.0)
    assert clock_time(kb) == 5.0
    reset_clock(kb)
    assert clock_time(kb) == 0.0


def test_reset_clock_on_flip_fires_on_next_flip():
    kb = _FakeKeyboard()
    win = _FakeWindow()
    kb.clock.set(3.0)
    reset_clock_on_flip(kb, win)
    # Not reset until the flip actually happens.
    assert clock_time(kb) == 3.0
    win.flip()
    assert clock_time(kb) == 0.0


# ── wait_for_key / check_quit ─────────────────────────────────────────────────
#
# These wrap the backend-switching wait_for_keys / get_keys / clear_events, so we
# monkeypatch those module-level names to drive the quit/return logic without a
# real PsychoPy backend.


def test_wait_for_key_returns_pressed_name(monkeypatch):
    monkeypatch.setattr(kbd, "clear_events", lambda kb: None)
    monkeypatch.setattr(kbd, "wait_for_keys", lambda kb, keys: ["1"])
    assert wait_for_key(None, ["1", "2"]) == "1"


def test_wait_for_key_appends_quit_keys_to_the_wait(monkeypatch):
    seen = {}
    monkeypatch.setattr(kbd, "clear_events", lambda kb: None)

    def fake_wait(kb, keys):
        seen["keys"] = keys
        return ["1"]

    monkeypatch.setattr(kbd, "wait_for_keys", fake_wait)
    wait_for_key(None, ["1"], quit_keys=["escape"])
    assert seen["keys"] == ["1", "escape"]


def test_wait_for_key_runs_on_quit_for_quit_key(monkeypatch):
    monkeypatch.setattr(kbd, "clear_events", lambda kb: None)
    monkeypatch.setattr(kbd, "wait_for_keys", lambda kb, keys: ["escape"])
    quit_calls: list[bool] = []
    name = wait_for_key(
        None, ["1"], quit_keys=["escape"], on_quit=lambda: quit_calls.append(True)
    )
    assert name == "escape"
    assert quit_calls == [True]


def test_wait_for_key_does_not_quit_on_normal_key(monkeypatch):
    monkeypatch.setattr(kbd, "clear_events", lambda kb: None)
    monkeypatch.setattr(kbd, "wait_for_keys", lambda kb, keys: ["1"])
    quit_calls: list[bool] = []
    wait_for_key(None, ["1"], quit_keys=["escape"], on_quit=lambda: quit_calls.append(True))
    assert quit_calls == []


def test_wait_for_key_clear_first_toggles_clear_events(monkeypatch):
    cleared: list[bool] = []
    monkeypatch.setattr(kbd, "clear_events", lambda kb: cleared.append(True))
    monkeypatch.setattr(kbd, "wait_for_keys", lambda kb, keys: ["1"])
    wait_for_key(None, ["1"])
    assert cleared == [True]
    cleared.clear()
    wait_for_key(None, ["1"], clear_first=False)
    assert cleared == []


def test_check_quit_runs_on_quit_when_quit_key_buffered(monkeypatch):
    monkeypatch.setattr(kbd, "get_keys", lambda kb, keys: ["escape"])
    quit_calls: list[bool] = []
    check_quit(None, ["escape"], on_quit=lambda: quit_calls.append(True))
    assert quit_calls == [True]


def test_check_quit_noop_when_buffer_empty(monkeypatch):
    monkeypatch.setattr(kbd, "get_keys", lambda kb, keys: [])
    quit_calls: list[bool] = []
    check_quit(None, ["escape"], on_quit=lambda: quit_calls.append(True))
    assert quit_calls == []
