.PHONY: release bump-patch bump-minor bump-major version

# Current version, read straight from pyproject.toml.
VERSION := $(shell grep -m1 '^version = ' pyproject.toml | cut -d'"' -f2)

version:
	@echo $(VERSION)

# Cut a release: bump pyproject.toml to $(TO), commit, and tag v$(TO).
# Usage: make release TO=0.4.0
release:
	@test -n "$(TO)" || { echo "usage: make release TO=X.Y.Z"; exit 1; }
	@test -z "$$(git status --porcelain)" || { echo "working tree is dirty; commit or stash first"; exit 1; }
	@git rev-parse -q --verify "refs/tags/v$(TO)" >/dev/null && { echo "tag v$(TO) already exists"; exit 1; } || true
	sed -i '' 's/^version = ".*"/version = "$(TO)"/' pyproject.toml
	uv lock
	git add pyproject.toml uv.lock
	git commit -m "chore: release v$(TO)"
	git tag -a "v$(TO)" -m "v$(TO)"
	@echo "tagged v$(TO) — run 'git push && git push --tags' to publish"

# Convenience wrappers that compute the next version from the current one.
bump-patch:
	@$(MAKE) release TO=$(shell echo $(VERSION) | awk -F. '{printf "%d.%d.%d", $$1, $$2, $$3+1}')

bump-minor:
	@$(MAKE) release TO=$(shell echo $(VERSION) | awk -F. '{printf "%d.%d.0", $$1, $$2+1}')

bump-major:
	@$(MAKE) release TO=$(shell echo $(VERSION) | awk -F. '{printf "%d.0.0", $$1+1}')
