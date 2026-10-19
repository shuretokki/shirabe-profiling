<!--
SPDX-FileCopyrightText: Copyright © 2026 shuretokki
SPDX-License-Identifier: Apache-2.0
-->

# Contributing to shirabe-profiling

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/shuretokki/shirabe-profiling.git
cd shirabe-profiling
uv sync
```

With [Nix](https://nixos.org) and [direnv](https://direnv.net), `direnv allow` loads a shell that has `uv`, `just`, `git-cliff`, `gh`, and `nodejs`.
Run `just` to list the recipes.

## Running Tests

```bash
just test
```

## Checks

```bash
just full-check     # lock file, lint, format, basedpyright, README, licenses, and pytest (aliases: check, c, fc)
just lint --fix     # apply safe lint fixes
just fmt-write      # add trailing commas, then format with ruff (aliases: fmt, commas)
just fmt-check      # check the formatting and the commas without changing files
just typecheck      # basedpyright only
just docs-check     # the README code blocks parse, and its images and links exist
just license-check  # every file has a license and a copyright holder (REUSE)
```

The recipes need `uv`, `git-cliff`, and `gh` on the PATH, and the Nix shell has all three.
The docs site in `docs/` needs Node 24, which the Nix shell also has.
`just docs-dev` runs it with `nub` when that is installed, and with `npm` when it is not.
`just docs-build` builds the site, and `just docs-links` checks its links and anchors with lychee, which the Nix shell has.

## Licenses

`REUSE.toml` names the copyright holders and the license of every file, and `LICENSES/` holds one text for each license.
When you add work from someone else, such as a font or an icon, add an annotation for its files to `REUSE.toml`.
Then run `uvx reuse download --all` to fetch the license text, and run `just license-check` to make sure that every file is covered.
Keep the root `LICENSE` and `LICENSES/Apache-2.0.txt` the same text, which a test checks.

## Report logo

The report header shows no logo for now, and the README holds the wordmark.
To show one, copy `assets/logo/wordmark-inline.svg` to `src/shirabe_profiling/report/templates/logo-wordmark.svg`, and the header picks it up without a code change.
That file uses `currentColor`, so the logo follows the light and the dark theme, and `.brand-wordmark` in `report.css` sets its height.

## Changelog

`just changelog` prints a draft for the commits since the last tag.
It reads Conventional Commit messages (`feat:`, `fix:`, `perf:`, `chore(deps):`).
Rewrite the draft as plain sentences and put it in `CHANGELOG.md`.

## Releasing

1. `just bump 0.2.0` sets the version in `pyproject.toml`, `__init__.py`, and `uv.lock`, and drafts the `CHANGELOG.md` section from the `feat`, `fix`, and `perf` commits since the last tag.
2. Read the section and reword it if needed. `just changelog` prints a fresh draft without changing a file.
3. Commit both as `chore(release): 0.2.0`.
4. `just release --dry-run` checks everything and prints the release notes, and it changes nothing.
5. `just release` does the same, asks for a `y`, then tags `v0.2.0`, pushes main and the tag, and creates the GitHub release from the changelog section.
6. `just publish-test` and `just publish` upload to TestPyPI and PyPI.

The release stops unless you are on main with a clean tree that is not behind origin.
It also needs agreeing version files and a changelog section.
The package must meet the PyPI upload rules, and its version must not be on PyPI yet.
The full check must pass.
The uploads read their tokens from a `.env` file, which git ignores.
Copy `.env.example` to `.env` and fill in `UV_PUBLISH_TEST_TOKEN` for TestPyPI and `UV_PUBLISH_TOKEN` for PyPI.

To practice a release, use a pre-release version such as `0.2.0rc1`.
`just bump` accepts it, and `just release` marks the GitHub release as a pre-release.
Upload it with `just publish-test` only, and install it with `pip install --pre --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple shirabe-profiling`.
A PyPI release never changes, so delete the changelog section of the pre-release when you release the final version.

## README Screenshots

`just readme-images` makes the pictures and the scrolling videos in `assets/screenshots/` again, so run it after a change to the report design.
It builds a report from a synthetic dataset, crops each view with a headless browser, and needs an internet connection for the report scripts.
It needs Chrome, Chromium, or Edge, and you can set `BROWSER` to the program if the script cannot find it.
The videos also need `ffmpeg`, which `nix develop` provides.

## Code Style

- Line length: 99 characters
- A call or a function signature with two or more arguments has a trailing comma, so each argument sits on its own line (`just fmt` adds the commas, `just check` fails when one is missing)
- Type hints everywhere, `Any` only for opaque state
- Minimal comments — code should be self-explanatory, comments explain *why*, not *what*
- Import order: stdlib → third-party → project (enforced by `ruff`)
- Polars-native: no NumPy/SciPy/Pandas in core logic

## Pull Requests

1. Fork the repo and create a feature branch
2. Make your changes with tests
3. Run `just check` before submitting
4. Open a PR with a clear description of what and why

## Reporting Issues

Use [GitHub Issues](https://github.com/shuretokki/shirabe-profiling/issues) with the provided templates.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
