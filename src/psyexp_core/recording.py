"""
The generic CSV writer. A task defines its own record dataclasses and column
lists, then either uses ``CsvWriter`` directly or subclasses it to bind a fixed
schema. Each ``append`` pulls the named attributes off the record and flushes,
so a crash mid-run still leaves a complete file up to the last trial.
"""
from __future__ import annotations

import csv
from pathlib import Path


class CsvWriter:
    def __init__(self, path: Path, columns: list[str]) -> None:
        self._file = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=columns)
        self._writer.writeheader()
        self._columns = columns

    def append(self, record: object) -> None:
        row = {name: getattr(record, name) for name in self._columns}
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
