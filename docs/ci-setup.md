# Setting up PyPI CI (one-time)

This is the **one-time** setup that lets [`publish.yml`](../.github/workflows/publish.yml)
upload `psyexp-core` to PyPI. For the day-to-day release process (bump, tag,
publish the draft), see [releasing.md](releasing.md).

## How auth works: Trusted Publishing (OIDC), no stored token

We do **not** store a PyPI API token anywhere — not as a repo secret, not as an
environment secret. Instead the publish job uses **Trusted Publishing**: at run
time GitHub mints a short-lived OIDC token, and PyPI accepts the upload because it
matches a *trusted publisher* you registered (owner + repo + workflow + environment).

Why this is the safest option:

- There's no long-lived credential to leak — the token exists only for minutes,
  inside the one publish job.
- The token is scoped to the `pypi` **environment**, so only a run in that
  environment can mint it — not test/PR/push workflows.
- The `pypi` environment adds a **manual approval gate** before the job runs.

The publish job already declares this (no edits needed):

```yaml
# .github/workflows/publish.yml
permissions:
  id-token: write          # mint the OIDC token
environment:
  name: pypi               # gate + scope
```

## Step 1 — Create the `pypi` GitHub Environment + approval gate

GitHub auto-creates an environment on first use *without* protections, so this step
is only needed to add the reviewer gate (recommended).

**UI:** Repo → **Settings → Environments → New environment** → name it `pypi`.
Then under **Deployment protection rules**:

- Enable **Required reviewers** and add yourself (and/or a `@HAPNlab` team). The
  publish job will now pause and wait for an approval click before it runs.
- *(Optional)* **Deployment branches and tags** → *Selected* → add a tag rule like
  `v*` so only version tags can deploy to `pypi`.

**CLI alternative** (needs repo admin; reviewer IDs are numeric user/team IDs):

```sh
# create/configure the environment with a required reviewer
gh api -X PUT repos/HAPNlab/psyexp-core/environments/pypi \
  -F "reviewers[][type]=User" -F "reviewers[][id]=<YOUR_USER_ID>"
# look up your numeric id:
gh api users/<your-login> --jq .id
```

## Step 2 — Register the trusted publisher on PyPI

This tells PyPI to trust uploads from this repo's publish workflow.

### If the project does **not** exist on PyPI yet (first release)

Use a **pending publisher** — it creates the project on first successful upload:

1. Log in to PyPI → **Account settings → Publishing** (or
   <https://pypi.org/manage/account/publishing/>).
2. Under **Add a new pending publisher**, fill in:
   - **PyPI Project Name:** `psyexp-core`
   - **Owner:** `HAPNlab`
   - **Repository name:** `psyexp-core`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. Save.

### If the project already exists

Project page → **Manage → Publishing → Add a new publisher**, with the same
owner / repo / workflow / environment values above.

> The **Environment name must be exactly `pypi`** — it has to match the
> `environment: name:` in `publish.yml`, or PyPI will reject the OIDC token.

## Step 3 — Do a release

Follow [releasing.md](releasing.md): bump the version + `CHANGELOG.md`, `uv lock`,
tag `vX.Y.Z`. The tag drafts a GitHub Release; **publish the draft**. That triggers
`publish.yml`, which will:

1. run the test matrix and build the sdist/wheel, then
2. pause on the `pypi` environment for your **approval**, then
3. upload to PyPI via OIDC.

Approve it from the **Actions** run page (or the repo's **Environments** view).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `invalid-publisher` / OIDC rejected | The PyPI trusted publisher's owner/repo/workflow/**environment** don't all match. Re-check Step 2 — `pypi` and `publish.yml` are the usual culprits. |
| Job runs but never uploads / waits forever | It's parked on the environment approval gate. Approve it on the run page. |
| `File already exists` | That version is already on PyPI (versions are immutable). `skip-existing: true` turns this into a skip; bump the version to ship new code. See [releasing.md](releasing.md#retag--re-release-semantics). |
| `id-token` permission error | The job needs `permissions: id-token: write` (already set in `publish.yml`). |
