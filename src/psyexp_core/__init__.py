"""
psyexp-core: task-agnostic harness for PsychoPy experiments.

Submodules are import-tiered: ``diagnostics``, ``rundir``, ``recording``, and
``manifest`` are PsychoPy-free and safe to import anywhere; ``screen``,
``keyboard``, ``instructions``, and ``wizard`` pull in PsychoPy / GL / terminal
machinery and should be imported by the task entry point. Import from the
submodules directly to keep startup lean.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("psyexp-core")
except PackageNotFoundError:  # running from a raw checkout without install
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
