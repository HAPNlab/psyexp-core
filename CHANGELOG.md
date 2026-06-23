# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
See [docs/releasing.md](docs/releasing.md) for the release process.

## v0.5.1

### Added

- PyPI publishing on a published GitHub Release via Trusted Publishing (OIDC; no
  stored token).
- Draft GitHub Release creation on tag push, with notes pulled from this file.
- This changelog and a release guide ([docs/releasing.md](docs/releasing.md)).
- `[project.urls]` for the PyPI project page.

## v0.5.0

### Added

- Timed-press + keyboard-clock API in `keyboard`: `get_presses` (name + reaction
  time), `reset_clock_on_flip`, `reset_clock`, `clock_time`, and the `KeyPress`
  dataclass — so timing-critical response windows can read frame-accurate RT
  through the shared abstraction.

### Fixed

- `keyboard` imports PsychoPy lazily, so the module (and its PsychoPy-free
  timed-press / clock helpers) stays importable and unit-testable in headless/CI
  environments without the PsychoPy stack.

## v0.4.0

### Changed

- Instruction-pager page type uses a generic, so callers keep their own page type.

### Added

- Makefile for release automation.

## v0.3.0

### Added

- Loud warning when psychtoolbox is unavailable and the keyboard falls back to
  PsychoPy's focus-dependent `event` backend.

## v0.2.0

### Fixed

- Poll for keyboard input rather than blocking, so the window keeps flipping (and
  can come to the foreground to receive keys) on macOS.

### Added

- Co-development instructions for overlaying an editable checkout over a git pin.

## v0.1.0

Initial release: the task-agnostic harness — `screen` (fullscreen window +
frame-timing calibration), `diagnostics`, `rundir`, `manifest`, `recording`
(`CsvWriter`), `wizard` setup primitives, the `instructions` pager, and the
`keyboard` PTB/event abstraction — with the version resolved from `pyproject.toml`
and CI for tests and release checks.
