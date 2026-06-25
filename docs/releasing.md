# Release Guide

How releases of `psyexp-core` are versioned, verified, and published.

`psyexp-core` is a shared library: its consumers (e.g. `mid-task-deterministic`,
`heat-task`) pin a version and record `psyexp_core_version` in every run manifest.
**A release is a promise about the public API** — the modules and functions in
`src/psyexp_core/` that tasks import. Breaking that contract is a major change.

## Versioning (SemVer)

We follow [Semantic Versioning 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`,
applied to the **public API** (the symbols re-exported from each module).

- **MAJOR** — backward-incompatible API changes: removing/renaming a function,
  changing a signature or return type, or altering documented behavior a consumer
  relies on (e.g. `get_keys` returning a different type).
- **MINOR** — backward-compatible additions: a new function, a new optional
  parameter, a new module. Existing callers keep working untouched.
- **PATCH** — backward-compatible bug fixes and docs that don't change the API.

> Rule of thumb: if a pinned consumer would need a code change to upgrade, it's at
> least MINOR (if only to opt in) and MAJOR if their *existing* code would break.

While iterating below 1.0, prefer bumping MINOR for anything consumers must adopt.

The version lives in two places that must stay in sync, plus the lockfile:

- `pyproject.toml` → `[project].version`
- `CHANGELOG.md` → a heading for that version
- `uv.lock` → the project's own pinned version (run `uv lock` after bumping)

The git tag is the same version prefixed with `v` (e.g. `v0.6.0`). The
[release workflow](../.github/workflows/release.yml) enforces all three agree and
fails the release otherwise.

## Pre-releases

For changes not yet ready to pin, publish a pre-release using a SemVer suffix:

| Suffix | Meaning |
|--------|---------|
| `-alpha.N` | Early; API may still change. |
| `-beta.N`  | API stabilizing, under test. |
| `-rc.N`    | Release candidate; final sign-off pending. |

Examples: `v0.6.0-alpha.1`, `v0.6.0-rc.1`. The [release workflow](../.github/workflows/release.yml)
marks any tag with an `-alpha`/`-beta`/`-rc` suffix as a GitHub **pre-release**.

For throwaway iteration you can instead publish PyPI pre-release versions
(`0.6.0rc1`, `0.6.0.dev3`) — each is a distinct, disposable version on PyPI.

## Verification before a release

1. **Tests pass on the full matrix** (3.11 / 3.12 / 3.13) and lint is clean:
   ```bash
   uv run --no-sync pytest
   uv run --no-sync ruff check
   ```
   CI runs these on every tag via [release-check](../.github/workflows/release.yml).
2. **The public API change is intended and SemVer-classified** — confirm the bump
   level matches what changed (see above), and that `CHANGELOG.md` describes it.
3. **Downstream still builds.** For a MINOR/MAJOR, smoke-test the consumers against
   the new core by overlaying it (`uv pip install -e ../psyexp-core`, then
   `uv run --no-sync pytest` in the task repo) before tagging.

## Cutting a release

1. **Verify** per the checklist above (or choose a pre-release suffix).
2. **Bump the version** in `pyproject.toml`.
3. **Update `CHANGELOG.md`:** move the `## Unreleased` entries under a new heading
   matching the tag without the leading `v` (e.g. `## v0.6.0`).
4. **Re-lock:** `uv lock` (updates the project's own version in `uv.lock`).
5. **Commit** the bump (e.g. `chore(release): v0.6.0`) and merge to `main`.
6. **Tag and push:**
   ```bash
   git tag v0.6.0          # or v0.6.0-rc.1 for a pre-release
   git push origin v0.6.0
   ```
   The [release workflow](../.github/workflows/release.yml) runs the tests, checks
   the version/changelog/lock agree, and **publishes** a GitHub Release with
   notes from `CHANGELOG.md` (marked pre-release for `-alpha`/`-beta`/`-rc` tags).
7. The same [release workflow](../.github/workflows/release.yml) then builds the
   sdist/wheel and uploads to [PyPI](https://pypi.org/project/psyexp-core/) via
   Trusted Publishing. Its PyPI step runs in the `pypi` environment and **waits for
   reviewer approval** — approve it from the workflow run to ship, or reject to abort.

> The tag publishes a Release and builds the wheel automatically; **the PyPI upload
> still gates on the `pypi` environment approval.** A human approves that step before
> anything ships.

## Retag / re-release semantics

Because the PyPI upload gates on the `pypi` environment approval, not on the tag or
Release existing, tags stay cheap:

- **Moving or deleting a tag** before approving the PyPI step: fine — nothing was
  sent to PyPI. (Delete the auto-published Release too, e.g. `make delete-tag`.)
- **PyPI versions are immutable:** once `X.Y.Z` is uploaded, that number is burned —
  you can *yank* it but never re-upload it, even to a different commit. Re-publishing
  the same version is rejected; `skip-existing: true` makes the publish job skip
  rather than fail. To ship corrected code, **bump the version**.
- For disposable iteration, use a pre-release version (`X.Y.ZrcN` / `X.Y.Z.devN`).

## One-time PyPI setup (Trusted Publishing)

No API token is stored: the publish job authenticates via OIDC, scoped to the
`pypi` GitHub Environment (which also gates publishes behind a required-reviewer
approval). The full one-time setup — creating the environment + gate and
registering the trusted publisher on PyPI — is in
**[ci-setup.md](ci-setup.md)**.
