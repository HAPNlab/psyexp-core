"""Tests for the timed-press + keyboard-clock helpers.

These read a Keyboard object directly, so they're exercised with a small fake
keyboard / window that mimics PsychoPy's getKeys / callOnFlip / clock surface.
"""
from __future__ import annotations

from psyexp_core.keyboard import (
    KeyPress,
    clock_time,
    get_presses,
    reset_clock,
    reset_clock_on_flip,
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
