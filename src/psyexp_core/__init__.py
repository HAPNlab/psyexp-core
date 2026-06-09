"""
psyexp-core: task-agnostic harness for PsychoPy experiments.

Submodules are import-tiered: ``diagnostics``, ``rundir``, ``recording``, and
``manifest`` are PsychoPy-free and safe to import anywhere; ``screen``,
``keyboard``, ``instructions``, and ``wizard`` pull in PsychoPy / GL / terminal
machinery and should be imported by the task entry point. Import from the
submodules directly to keep startup lean.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
