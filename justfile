# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

set default-list := true
set dotenv-load := true
set shell := ["bash", "-euo", "pipefail", "-c"]

# https://docs.astral.sh/uv
uv := require("uv")

PATHS := "src tests scripts"

# Install the project and its dev tools
sync:
    uv sync

# Run dekit, which starts the dev tasks in dekit.yaml: just dekit up
[group("dev")]
@dekit *args:
    uv run dekit {{ args }}

# Serve the documentation site in docs/ with live reload, using nub when it is installed and npm if not
[group("dev")]
[script("bash")]
[working-directory("docs")]
docs-dev: _docs-images
    set -euo pipefail
    if command -v nub >/dev/null; then
      nub run dev
    elif command -v npm >/dev/null; then
      npm run dev
    else
      echo "error: install node.js or nub to run the docs site" >&2
      exit 1
    fi

# Build the documentation site in docs/ into docs/.output/public, using nub when it is installed and npm if not
[group("dev")]
[script("bash")]
[working-directory("docs")]
docs-build: _docs-images
    set -euo pipefail
    if command -v nub >/dev/null; then
      nub run build
    elif command -v npm >/dev/null; then
      npm run build
    else
      echo "error: install node.js or nub to build the docs site" >&2
      exit 1
    fi

# Check the links and anchors of the built docs site without network access (run just docs-build first)
[group("checks")]
@docs-links:
    test -d docs/.output/public || { echo "error: run just docs-build first" >&2; exit 1; }
    {{ require("lychee") }} --offline --include-fragments=anchor-only --root-dir "$PWD/docs/.output/public" --no-progress --format compact 'docs/.output/public/**/*.html'

# Copy the report screenshots that the docs pages link into the docs site.
@_docs-images:
    mkdir -p docs/public/images
    { grep -rhoE '/images/report-[a-z-]+\.png' docs/content || true; } | sort -u | sed 's#^/images/##' | while read -r name; do cp "assets/screenshots/$name" docs/public/images/; done

# Remake the README screenshots in assets/screenshots/ (needs Chrome, Chromium, or Edge, and internet access)
@readme-images:
    uv run python scripts/readme_images.py assets/screenshots

# Print a CHANGELOG.md draft for the commits since the last tag, without changing a file
[group("release")]
@changelog:
    {{ require("git-cliff") }} --unreleased --tag "v$(just _version)" 2>/dev/null

# Set a new version in pyproject.toml and in __init__.py, and draft the CHANGELOG.md section
[group("release")]
[script("bash")]
bump version:
    set -euo pipefail
    new="{{ version }}"
    if ! [[ "$new" =~ ^[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+|\.dev[0-9]+)?$ ]]; then
      echo "error: the version must look like 1.2.3 or 1.2.3rc1, not $new" >&2
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
    if ! grep -q "^## \[$new\]" CHANGELOG.md; then
      draft=$(mktemp)
      {{ require("git-cliff") }} --unreleased --tag "v$new" 2>/dev/null > "$draft"
      awk -v f="$draft" '!done && /^## \[/ { while ((getline line < f) > 0) print line; print ""; done = 1 } { print }' CHANGELOG.md > CHANGELOG.md.new
      mv CHANGELOG.md.new CHANGELOG.md
      rm -f "$draft"
      echo "drafted the CHANGELOG.md section for $new from the commits"
    fi
    echo "$old -> $new in pyproject.toml, src/shirabe_profiling/__init__.py and uv.lock"
    echo "next: read the CHANGELOG.md section for $new and reword it if needed"
    echo "then commit the files as chore(release): $new, and run just release"

# Build the wheel and the source archive into dist/
[group("release")]
build:
    uv build

# Tag the version in pyproject.toml, push it and create the GitHub Release
[group("release")]
[script("bash")]
release *flags:
    set -euo pipefail
    dry=false
    [ "{{ flags }}" = "--dry-run" ] && dry=true
    version=$(just _version)
    tag="v$version"
    prerelease=""
    if [[ "$version" =~ ((a|b|rc)[0-9]+|\.dev[0-9]+)$ ]]; then prerelease="--prerelease"; fi
    fail() { echo "error: $*" >&2; exit 1; }

    [ "$(git branch --show-current)" = main ] || fail "release from main, not $(git branch --show-current)"
    [ -z "$(git status --porcelain)" ] || fail "commit or stash these first: $(git status --short | tr '\n' ' ')"
    git rev-parse -q --verify "refs/tags/$tag" >/dev/null && fail "the tag $tag already exists"
    [ -z "$(git ls-remote --tags origin "$tag")" ] || fail "the tag $tag already exists on origin"
    git fetch -q origin main
    [ "$(git rev-list --count HEAD..origin/main)" -eq 0 ] || fail "origin/main has commits that this branch does not have, pull first"

    # release notes are the CHANGELOG.md section for this version.
    notes=$(mktemp)
    trap 'rm -f "$notes"' EXIT
    awk -v v="$version" '
      $0 ~ "^## \\[" v "\\]" { on = 1; next }
      /^## \[/ { on = 0 }
      /^\[[^]]+\]: / { on = 0 }
      on
    ' CHANGELOG.md > "$notes"
    grep -q '[^[:space:]]' "$notes" || fail "CHANGELOG.md has no section for $version, add \"## [$version] - $(date +%F)\""

    just _validate
    just full-check

    echo ""
    echo "release notes:"
    cat "$notes"
    echo ""
    echo "ready: tag $tag at $(git rev-parse --short HEAD), push main and $tag, create the GitHub Release"
    if [ "$dry" = true ]; then
      echo "dry run, nothing was changed"
      exit 0
    fi
    read -r -p "continue? [y/N] " answer
    [ "$answer" = y ] || fail "stopped, nothing was changed"

    git tag -a "$tag" -m "$version"
    git push origin main
    git push origin "$tag"
    {{ require("gh") }} release create "$tag" --verify-tag $prerelease --title "shirabe-profiling $version" --notes-file "$notes"
    echo "next: just publish-test, then just publish"

# Upload this version to TestPyPI, the practice index (needs UV_PUBLISH_TEST_TOKEN in .env)
[group("release")]
[script("bash")]
publish-test: _guard-tagged build
    set -euo pipefail
    : "${UV_PUBLISH_TEST_TOKEN:?add UV_PUBLISH_TEST_TOKEN to .env}"
    v=$(just _version)
    uv publish --token "$UV_PUBLISH_TEST_TOKEN" --publish-url https://test.pypi.org/legacy/ "dist/shirabe_profiling-$v"*

# Upload this version to PyPI (needs UV_PUBLISH_TOKEN in .env, or trusted publishing)
[group("release")]
[confirm("Upload this version to PyPI? A release cannot be changed or deleted afterwards.")]
[script("bash")]
publish: _guard-tagged build
    set -euo pipefail
    v=$(just _version)
    uv publish "dist/shirabe_profiling-$v"*

# Run lock file, lint, format, types, docs, licenses and tests
[group("checks")]
@full-check:
    just _run-with-status lock-check
    just _run-with-status lint
    just _run-with-status fmt-check
    just _run-with-status typecheck
    just _run-with-status docs-check
    just _run-with-status license-check
    just _run-with-status test -q
    echo ""
    echo "All checks passed."
alias check := full-check
alias c := full-check
alias fc := full-check

# Check that uv.lock matches pyproject.toml
[group("checks")]
@lock-check:
    uv lock --check

# Lint with ruff, and pass --fix to apply safe fixes: just lint --fix
[group("checks")]
@lint *args:
    uv run ruff check {{ args }} {{ PATHS }}

# Check the formatting and the trailing commas without changing files
[group("checks")]
@fmt-check:
    uv run ruff format --check {{ PATHS }}
    uv run python scripts/add_commas.py --check {{ PATHS }}

# Add trailing commas to calls and signatures with 2 or more arguments, then format
[group("checks")]
@fmt-write:
    uv run python scripts/add_commas.py {{ PATHS }}
    uv run ruff format {{ PATHS }}
    uv run ruff check --fix --select COM812 {{ PATHS }}
    uv run ruff format {{ PATHS }}
alias fmt := fmt-write
alias commas := fmt-write

# Type-check the project, or only the given files: just typecheck src/shirabe_profiling/target.py
[group("checks")]
@typecheck *files:
    uv run basedpyright {{ files }}

# Check that the README code blocks parse and that its local images and links exist
[group("checks")]
@docs-check:
    uv run python scripts/docs_check.py

# Check that every file has a license and a copyright holder, and that LICENSES/ matches (REUSE)
[group("checks")]
@license-check:
    uvx reuse lint

# Run the tests, or only some: just test tests/test_target.py -k leakage
[group("test")]
@test *args:
    uv run pytest {{ args }}
alias t := test

# Run the tests with a coverage report
[group("test")]
@cov:
    uv run pytest --cov=shirabe_profiling --cov-report=term-missing

# Add license headers from the REUSE.toml rules, templates excluded: just annotate --dry-run, --replace to rewrite, or limit it to a path
[group("maintenance")]
@annotate *args:
    uv run python scripts/annotate_from_reuse.py --exclude "**/*.j2" --exclude "**/*.html" --exclude "**/*.svg" --exclude "**/*.vue" {{ args }}

# Delete the build output and the tool caches
[group("maintenance")]
@clean:
    rm -rf dist build .pytest_cache .ruff_cache .basedpyright

# Upgrade the locked versions of the dependencies, then reinstall
[group("maintenance")]
update:
    uv lock --upgrade
    uv sync

# List the direct dependencies that have a newer version
[group("maintenance")]
@outdated:
    uv tree --outdated --depth 1

# Run a recipe with a status line before and after
@_run-with-status recipe *args:
    echo ""
    echo "→ {{ recipe }}"
    just {{ recipe }} {{ args }}
    echo "✓ {{ recipe }}"

# The version in pyproject.toml.
@_version:
    grep -m1 '^version' pyproject.toml | cut -d'"' -f2

# Check the rules that PyPI enforces when you upload, and the ones of this repository.
# The PyPI rules come from the upload code of Warehouse, see scripts/check_package.py.
[script("bash")]
_validate:
    set -euo pipefail
    version=$(just _version)
    status=0
    fail() { echo "error: $*" >&2; status=1; }

    init=$(grep -m1 '^__version__' src/shirabe_profiling/__init__.py | cut -d'"' -f2)
    [ "$init" = "$version" ] || fail "pyproject.toml says $version but __init__.py says $init, run just bump"
    grep -q "^## \[$version\]" CHANGELOG.md || fail "CHANGELOG.md has no section for $version"

    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    if uv build --out-dir "$tmp" >/dev/null 2>&1; then
      # wheel must hold the typing marker and the report assets.
      listing=$(uv run python -m zipfile -l "$tmp"/*.whl)
      for needed in py.typed report/templates/report.html.j2 report/templates/favicon.svg; do
        grep -q "$needed" <<<"$listing" || fail "the wheel does not hold $needed"
      done
      # twine is the check that the Python Packaging guide names for the README and the metadata.
      uvx twine check --strict "$tmp"/* >/dev/null 2>&1 || fail "twine check failed, run uvx twine check --strict dist/*"
      uv run python scripts/check_package.py "$tmp" || status=1
    else
      fail "uv build failed"
    fi

    # pypi refuses a file name that it has seen before, even after a delete.
    code=$(curl -s -o /dev/null -w '%{http_code}' "https://pypi.org/pypi/shirabe-profiling/$version/json" || true)
    case "$code" in
      200) fail "shirabe-profiling $version is already on PyPI, bump the version" ;;
      404) ;;
      *) echo "warning: could not ask PyPI about $version (HTTP $code)" >&2 ;;
    esac

    [ "$status" -eq 0 ] && echo "release rules ok"
    exit "$status"

# Stops unless HEAD carries the tag of the version in pyproject.toml.
[script("bash")]
_guard-tagged:
    set -euo pipefail
    v=$(just _version)
    if [ "$(git describe --exact-match --tags HEAD 2>/dev/null || true)" != "v$v" ]; then
      echo "error: HEAD is not tagged v$v, run just release first" >&2
      exit 1
    fi
