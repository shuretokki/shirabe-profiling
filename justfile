set default-list := true
set shell := ["bash", "-euo", "pipefail", "-c"]

PATHS := "src tests scripts"

# Install the project and its dev tools
sync:
    uv sync

# Run the tests, or only some: just test tests/test_target.py -k leakage
[group("checks")]
test *args:
    uv run pytest {{ args }}
alias t := test

# Run the tests with a coverage report
[group("checks")]
cov:
    uv run pytest --cov=shirabe_profiling --cov-report=term-missing

# Type-check the project, or only the given files: just typecheck src/shirabe_profiling/target.py
[group("checks")]
typecheck *files:
    uv run basedpyright {{ files }}

# Lint with ruff; pass --fix to apply safe fixes: just lint --fix
[group("checks")]
lint *args:
    uv run ruff check {{ args }} {{ PATHS }}

# Add trailing commas to calls and signatures with 2 or more arguments, then format
[group("checks")]
commas:
    uv run python scripts/add_commas.py {{ PATHS }}
    uv run ruff format {{ PATHS }}
    uv run ruff check --fix --select COM812 {{ PATHS }}
    uv run ruff format {{ PATHS }}

# Format all code: add trailing commas, then ruff format
[group("checks")]
fmt: commas

# Read-only gate: lock file, lint, format check, trailing commas, type check, tests (no files changed)
[group("checks")]
check:
    uv lock --check
    uv run ruff check {{ PATHS }}
    uv run ruff format --check {{ PATHS }}
    uv run python scripts/add_commas.py --check {{ PATHS }}
    uv run basedpyright
    uv run pytest -q
alias c := check

# Build the wheel and the source archive into dist/
[group("release")]
build:
    uv build

# Remake the README screenshots in docs/ (needs Chrome, Chromium, or Edge, and internet access)
[group("docs")]
readme-images:
    uv run python scripts/readme_images.py docs

# Print a CHANGELOG.md draft for the commits since the last tag
[group("release")]
@changelog:
    git-cliff --unreleased --tag "v$(just _version)" 2>/dev/null

# Set a new version in pyproject.toml and in __init__.py
[group("release")]
[script("bash")]
bump version:
    set -euo pipefail
    new="{{ version }}"
    if ! [[ "$new" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "error: the version must look like 1.2.3, not $new" >&2
      exit 1
    fi
    old=$(just _version)
    if [ "$old" = "$new" ]; then
      echo "error: pyproject.toml is already at $new" >&2
      exit 1
    fi
    o=${old//./\\.}
    sed -i "s/^version = \"$o\"/version = \"$new\"/" pyproject.toml
    sed -i "s/^__version__ = \"$o\"/__version__ = \"$new\"/" src/shirabe_profiling/__init__.py
    uv lock --quiet
    echo "$old -> $new in pyproject.toml, src/shirabe_profiling/__init__.py and uv.lock"
    echo "next: write the CHANGELOG.md section for $new (just changelog prints a draft)"

# Print the CHANGELOG.md section of the version in pyproject.toml
[group("release")]
[script("bash")]
release-notes:
    set -euo pipefail
    v=$(just _version)
    awk -v v="$v" '$0 ~ "^## \\[" v "\\]" { found = 1; next } /^## \[/ { found = 0 } found' CHANGELOG.md

# Commit the version bump and the changelog as a release, then tag it (nothing is pushed)
[group("release")]
[script("bash")]
release: _release-guards check build
    set -euo pipefail
    v=$(just _version)
    git add pyproject.toml uv.lock src/shirabe_profiling/__init__.py CHANGELOG.md
    git commit -m "chore(release): v$v"
    just tag
    echo "next: just push, then just publish and just gh-release"

# Tag HEAD as v<version> with an annotated tag (just release does this for you)
[group("release")]
[script("bash")]
tag:
    set -euo pipefail
    v=$(just _version)
    if git rev-parse -q --verify "refs/tags/v$v" >/dev/null; then
      echo "error: the tag v$v already exists" >&2
      exit 1
    fi
    git tag -a "v$v" -m "v$v"
    echo "tagged v$v at $(git rev-parse --short HEAD)"

# Push main and the release tag to origin
[group("release")]
[confirm("Push main and its tags to origin?")]
push:
    git push origin main --follow-tags

# Upload this version to TestPyPI, the practice index (needs UV_PUBLISH_TOKEN for TestPyPI)
[group("release")]
[script("bash")]
publish-test: _guard-tagged build
    set -euo pipefail
    v=$(just _version)
    uv publish --publish-url https://test.pypi.org/legacy/ "dist/shirabe_profiling-$v"*

# Upload this version to PyPI (needs UV_PUBLISH_TOKEN, or trusted publishing)
[group("release")]
[confirm("Upload this version to PyPI? A release cannot be changed or deleted afterwards.")]
[script("bash")]
publish: _guard-tagged build
    set -euo pipefail
    v=$(just _version)
    uv publish "dist/shirabe_profiling-$v"*

# Create the GitHub release from the tag, with the built files and the changelog section
[group("release")]
[confirm("Create the GitHub release for this version?")]
[script("bash")]
gh-release: _need-gh _guard-tagged build
    set -euo pipefail
    v=$(just _version)
    notes=$(mktemp)
    just release-notes > "$notes"
    gh release create "v$v" "dist/shirabe_profiling-$v"* --title "v$v" --notes-file "$notes"
    rm -f "$notes"

# Delete the build output and the tool caches
[group("maintenance")]
clean:
    rm -rf dist build .pytest_cache .ruff_cache .basedpyright

# Upgrade the locked versions of the dependencies, then reinstall
[group("maintenance")]
update:
    uv lock --upgrade
    uv sync

# List the direct dependencies that have a newer version
[group("maintenance")]
outdated:
    uv tree --outdated --depth 1

# The version in pyproject.toml.
@_version:
    grep -m1 '^version' pyproject.toml | cut -d'"' -f2

# Stops a release unless it starts from an up-to-date main with only the release files changed.
[script("bash")]
_release-guards:
    set -euo pipefail
    v=$(just _version)
    init=$(grep -m1 '^__version__' src/shirabe_profiling/__init__.py | cut -d'"' -f2)
    if [ "$init" != "$v" ]; then
      echo "error: pyproject.toml says $v but __init__.py says $init, run just bump" >&2
      exit 1
    fi
    branch=$(git branch --show-current)
    if [ "$branch" != "main" ]; then
      echo "error: a release starts from main, but this is $branch" >&2
      exit 1
    fi
    if git rev-parse -q --verify "refs/tags/v$v" >/dev/null; then
      echo "error: the tag v$v already exists, run just bump first" >&2
      exit 1
    fi
    if ! grep -q "^## \[$v\]" CHANGELOG.md; then
      echo "error: CHANGELOG.md has no section for $v (just changelog prints a draft)" >&2
      exit 1
    fi
    git fetch --quiet origin main
    if [ "$(git rev-list --count HEAD..origin/main)" -gt 0 ]; then
      echo "error: origin/main has commits that this branch does not have, pull first" >&2
      exit 1
    fi
    other=$(git status --porcelain --untracked-files=no | grep -v -E ' (pyproject\.toml|uv\.lock|CHANGELOG\.md|src/shirabe_profiling/__init__\.py)$' || true)
    if [ -n "$other" ]; then
      echo "error: these files changed outside the release files:" >&2
      echo "$other" >&2
      exit 1
    fi

# Stops unless HEAD carries the tag of the version in pyproject.toml.
[script("bash")]
_guard-tagged:
    set -euo pipefail
    v=$(just _version)
    if [ "$(git describe --exact-match --tags HEAD 2>/dev/null || true)" != "v$v" ]; then
      echo "error: HEAD is not tagged v$v, run just release first" >&2
      exit 1
    fi

# Stops with a clear message when the GitHub command line is missing.
@_need-gh:
    : {{ require("gh") }}
