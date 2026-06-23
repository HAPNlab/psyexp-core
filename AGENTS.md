# psyexp-core

Task-agnostic harness shared by the lab's PsychoPy task repos (`heat-task`,
`mid-task`, `mid-task-deterministic`). It owns the plumbing every task
duplicates — screen/frame-timing setup, run manifests, CSV writers, setup-wizard
primitives, the instruction pager, and the keyboard abstraction. Source lives in
`src/psyexp_core/`; tests in `tests/`.

## Conventions

- Python 3.11 only (PsychoPy caps at `<3.12`). Keep `requires-python` in sync.
- PsychoPy is imported lazily so the package stays importable/testable headless.
- Run `uv run ruff check` and `uv run pytest` before committing.

## Releases

Cutting a release is automated via the `Makefile` — don't bump the version by
hand. From a clean working tree:

- `make release TO=X.Y.Z` — bump `pyproject.toml`, relock, commit, and tag `vX.Y.Z`.
- `make bump-patch` / `make bump-minor` / `make bump-major` — compute the next
  version from the current one and run `release`.
- `make version` — print the current version.

Then `git push && git push --tags`. Tagging triggers a draft GitHub Release (notes
from `CHANGELOG.md`), and publishing that release uploads to PyPI via Trusted
Publishing. Update `CHANGELOG.md` under the new version *before* tagging. See
[docs/releasing.md](docs/releasing.md) for the full process.
