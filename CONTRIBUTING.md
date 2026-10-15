# Contributing to shirabe-profiling

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/shuretokki/shirabe-profiling.git
cd shirabe-profiling
uv sync
```

With [Nix](https://nixos.org) and [direnv](https://direnv.net), `direnv allow` loads a shell that has `uv`, `just`, and `git-cliff`.
Run `just` to list the recipes.

## Running Tests

```bash
just test
```

## Checks

```bash
just check      # ruff lint, ruff format check, trailing commas, basedpyright, pytest
just lint --fix # apply safe lint fixes
just fmt        # add trailing commas, then format with ruff
just commas     # same as fmt
just typecheck  # basedpyright only
```

## Changelog

`just changelog` prints a draft for the commits since the last tag.
It reads Conventional Commit messages (`feat:`, `fix:`, `perf:`, `chore(deps):`).
Rewrite the draft as plain sentences and put it in `CHANGELOG.md`.

## README Screenshots

`just readme-images` makes the pictures in `docs/` again, so run it after a change to the report design.
It builds a report from a synthetic dataset, crops each view with a headless browser, and needs an internet connection for the report scripts.
It needs Chrome, Chromium, or Edge, and you can set `BROWSER` to the program if the script cannot find it.

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
