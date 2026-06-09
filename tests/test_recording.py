"""Tests for the generic CsvWriter."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from psyexp_core.recording import CsvWriter

COLUMNS = ["trial_n", "label", "value"]


@dataclass
class _Rec:
    trial_n: int
    label: str
    value: float


def test_csv_writer_roundtrip(tmp_path: Path):
    path = tmp_path / "out.csv"
    w = CsvWriter(path, COLUMNS)
    w.append(_Rec(trial_n=1, label="a", value=1.5))
    w.append(_Rec(trial_n=2, label="b", value=2.0))
    w.close()

    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert set(rows[0].keys()) == set(COLUMNS)
    assert rows[0]["label"] == "a"
    assert rows[1]["trial_n"] == "2"


def test_csv_writer_flushes_each_row(tmp_path: Path):
    # A crash mid-run should still leave a complete file up to the last append.
    path = tmp_path / "out.csv"
    w = CsvWriter(path, COLUMNS)
    w.append(_Rec(trial_n=1, label="a", value=1.5))
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1  # readable before close()
    w.close()


def test_csv_writer_only_emits_declared_columns(tmp_path: Path):
    @dataclass
    class _Wide:
        trial_n: int
        label: str
        value: float
        extra: str  # not in COLUMNS — must be ignored

    path = tmp_path / "out.csv"
    w = CsvWriter(path, COLUMNS)
    w.append(_Wide(trial_n=1, label="a", value=1.5, extra="ignored"))
    w.close()
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert "extra" not in rows[0]
