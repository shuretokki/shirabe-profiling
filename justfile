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

# Read-only gate: lint, format check, trailing commas, type check, tests (no files changed)
[group("checks")]
check:
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

# The version in pyproject.toml.
@_version:
    grep -m1 '^version' pyproject.toml | cut -d'"' -f2
