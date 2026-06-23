# psyexp-core

Task-agnostic harness for PsychoPy experiments, shared across the lab's task
repos (`heat-task`, `mid-task`, `mid-task-deterministic`). It owns the *plumbing*
that every task duplicates; each task repo keeps only its own stimuli, trial
logic, and record schemas.

## What's in here

| Module | Responsibility |
| --- | --- |
| `screen` | `setup_screen()` — open a fullscreen PsychoPy window, enable VSYNC, run a frame-timing calibration, and return a `ScreenDiagnostics`. |
| `diagnostics` | The `ScreenDiagnostics` dataclass (import-light; no PsychoPy). |
| `rundir` | `make_run_dir(data_dir, label, session_time)` — timestamped output directory. |
| `manifest` | `write_manifest(...)` + `system_info()` — JSON run manifest with system/display/process diagnostics and the resolved `psyexp_core_version`. App-specific fields are injected via `header` / `study_params`. |
| `recording` | `CsvWriter` base class (maps a dataclass record onto a fixed column schema). |
| `wizard` | questionary / prompt_toolkit setup-wizard primitives: shared styles, `ask_text` / `ask_select` / `ask_confirm`, `PosFloatValidator`, `prompt_unique_name`, `quit_app`. |
| `instructions` | `page_through(...)` — a self-paced, keypress-driven instruction pager. |
| `keyboard` | PTB / PsychoPy-event keyboard abstraction: `build_keyboard` / `get_keys` / `wait_for_keys` / `clear_events`, plus the timed-press API for response windows — `get_presses` (name + rt), `reset_clock_on_flip` / `reset_clock` / `clock_time`. |

## Use from a task repo

Add it as a dependency. For day-to-day development, point at a local checkout so
edits are live without reinstalling:

```toml
# your-task/pyproject.toml
dependencies = ["psyexp-core"]

[tool.uv.sources]
psyexp-core = { path = "../psyexp-core", editable = true }
```

For a reproducible release build, pin a tagged ref instead:

```toml
[tool.uv.sources]
psyexp-core = { git = "ssh://git@github.com/<you>/psyexp-core.git", tag = "v0.1.0" }
```

`write_manifest` records the resolved `psyexp_core_version` so each run is
traceable back to a core version.

### Co-developing core while a task repo keeps the git pin

Lab task repos (e.g. `heat-task`) commit the **git-tag** source above so clones
reproduce exactly, then overlay a local editable install for development:

```bash
uv pip install -e ../psyexp-core
```

**Gotcha:** `uv run` re-syncs the task venv from its `uv.lock` on every launch,
which reverts that editable install straight back to the pinned tag (symptoms:
your local core edits silently don't take effect). Set `UV_NO_SYNC=1` in the task
repo (export it in your shell, or use `uv run --no-sync`) so the editable overlay
sticks; run a manual `uv sync` only when you change other deps, then re-run the
editable install. See heat-task's README ("Co-developing `psyexp-core` locally")
for the full workflow.

## Releasing

Tagging and publishing are deliberately separate, so tags stay cheap to iterate on:

1. **Bump + lock.** Update `version` in `pyproject.toml`, run `uv lock`, commit, and
   merge to `main`.
2. **Tag.** `git tag vX.Y.Z && git push origin vX.Y.Z`. This runs `release-check.yml`
   — the test matrix plus a guard that the tag, `pyproject.toml`, and `uv.lock`
   versions all agree. **Tagging does not publish anything.** Tags can be moved or
   deleted freely while iterating.
3. **Publish.** Create a GitHub Release for the tag. That — and only that — triggers
   `publish.yml`, which re-runs the tests, builds the sdist/wheel, and uploads to
   [PyPI](https://pypi.org/project/psyexp-core/) via **Trusted Publishing** (OIDC;
   no API token is stored).

### Retag / re-release semantics

PyPI versions are **immutable**: once `X.Y.Z` is published, that number is burned —
you can yank it, but never re-upload it, even to a different commit. So:

- **Moving/deleting a tag** before you've published a Release for it: totally fine —
  nothing was sent to PyPI.
- **Re-publishing the same version** (e.g. delete the Release and re-create it):
  PyPI rejects the duplicate; `skip-existing: true` makes the job skip rather than
  fail, but the old artifact stays. To ship new code you must bump the version.
- For throwaway iteration, use a **pre-release** version (`X.Y.ZrcN` / `X.Y.Z.devN`)
  — each is a distinct, disposable version on PyPI.

### One-time Trusted Publishing setup

On PyPI → the project's *Publishing* settings (or Account → Publishing for the very
first upload), add a GitHub trusted publisher: owner `HAPNlab`, repository
`psyexp-core`, workflow `publish.yml`, environment `pypi`.
