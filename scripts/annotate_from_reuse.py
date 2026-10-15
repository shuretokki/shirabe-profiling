# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Add or refresh license headers with the copyright and license from REUSE.toml."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SPDX_PREFIX = "SPDX-FileCopyrightText: "
CHUNK = 100
HEADER_LINES = 40

# a tag in any comment style tells that a file has a header.
ANY_TAG = re.compile(
    r"^\s*(?:#|//|--|;|%|/\*+|\*|<!--|\{#)\s*SPDX-(?:FileCopyrightText|License-Identifier):",
)
# only line comments can be removed line by line without breaking the file.
LINE_TAG = re.compile(r"^\s*(?:#|//|--|;|%)\s*SPDX-[A-Za-z-]+:")
EMPTY_COMMENT = re.compile(r"^\s*(?:#|//|--|;|%)\s*$")
# font and license texts carry their own copyright text, so they get no header.
LICENSE_TEXT = re.compile(r"(?i)(?:^|[-_.])(?:licen[cs]e|copying|ofl|notice)(?:[-_.]|$)")

Rule = tuple[tuple[str, ...], tuple[str, ...]]
Original = tuple[list[str], list[str]]


def as_tuple(value: str | list[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return (value,) if isinstance(value, str) else tuple(value)


def excluded(path: str) -> bool:
    """Return True for the license texts and the files that must stay free of headers."""
    name = path.rsplit(
        "/",
        1,
    )[-1]
    return (
        path.startswith("LICENSES/")
        or path == "REUSE.toml"
        or path.endswith(".license")
        or bool(LICENSE_TEXT.search(name))
    )


def in_roots(
    path: str,
    roots: list[str],
) -> bool:
    return any(root == "." or path == root or path.startswith(f"{root}/") for root in roots)


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Turn a REUSE.toml path glob into a regular expression."""
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith(
            "**/",
            i,
        ):
            parts.append("(?:.*/)?")
            i += 3
        elif pattern.startswith(
            "**",
            i,
        ):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "\\" and i + 1 < len(pattern):
            parts.append(re.escape(pattern[i + 1]))
            i += 2
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(parts))


def rules_from_toml(
    path: Path,
    files: list[str],
) -> dict[str, Rule]:
    if sys.version_info < (3, 11):
        raise SystemExit("--toml and --replace need Python 3.11 or newer, use --json instead")
    import tomllib

    annotations = tomllib.loads(path.read_text(encoding="utf-8")).get(
        "annotations",
        [],
    )
    rules: dict[str, Rule] = {}
    for annotation in annotations:
        patterns = [glob_to_regex(pattern.lstrip("/")) for pattern in as_tuple(annotation["path"])]
        rule = (
            as_tuple(annotation.get("SPDX-FileCopyrightText")),
            as_tuple(annotation.get("SPDX-License-Identifier")),
        )
        for file in files:
            if any(pattern.fullmatch(file) for pattern in patterns):
                # The last matching block wins, which is what reuse lint reports.
                rules[file] = rule
    return rules


def load_report(path: Path | None) -> dict[str, Any]:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    # reuse exits with 1 when it finds problems, but it still prints the report.
    result = subprocess.run(
        ["uvx", "reuse", "lint", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        raise SystemExit(f"reuse lint printed no report: {result.stderr.strip()}")
    return json.loads(result.stdout)


def rules_from_lint(report: dict[str, Any]) -> dict[str, Rule]:
    rules: dict[str, Rule] = {}
    for entry in report["files"]:
        found = entry["copyrights"] + entry["spdx_expressions"]
        # a file with a header or a .license file already has its own information.
        if any(item["source_type"] != "reuse-toml" for item in found):
            continue
        values = [item["value"] for item in entry["copyrights"]]
        if not all(value.startswith(SPDX_PREFIX) for value in values):
            print(f"skip {entry['path']}: its copyright prefix is not SPDX-FileCopyrightText")
            continue
        rules[entry["path"]] = (
            tuple(value.removeprefix(SPDX_PREFIX) for value in values),
            tuple(item["value"] for item in entry["spdx_expressions"]),
        )
    return rules


def project_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def read_lines(path: str) -> list[str] | None:
    """Return the lines of a text file with their endings, or None for a binary file."""
    try:
        return Path(path).read_bytes().decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return None


def write_lines(
    path: str,
    lines: list[str],
) -> None:
    Path(path).write_bytes("".join(lines).encode("utf-8"))


def has_header(lines: list[str]) -> bool:
    return any(ANY_TAG.match(line) for line in lines[:HEADER_LINES])


def has_values(
    lines: list[str],
    rule: Rule,
) -> bool:
    """Return True when the header holds every copyright and license of the rule."""
    text = "".join(lines[:HEADER_LINES])
    copyrights, licenses = rule
    # REUSE-IgnoreStart
    return all(f"{SPDX_PREFIX}{value}" in text for value in copyrights) and all(
        f"SPDX-License-Identifier: {identifier}" in text for identifier in licenses
    )
    # REUSE-IgnoreEnd


def strip_header(lines: list[str]) -> list[str] | None:
    """Return the lines without the SPDX header, or None if it is not a line comment."""
    first = next((i for i, line in enumerate(lines[:HEADER_LINES]) if LINE_TAG.match(line)), None)
    if first is None:
        return None
    start = first
    while start > 0 and EMPTY_COMMENT.match(lines[start - 1]):
        start -= 1
    end = first
    while end < len(lines) and (LINE_TAG.match(lines[end]) or EMPTY_COMMENT.match(lines[end])):
        end += 1
    # The blank line after the header goes too, so the new header brings its own.
    if end < len(lines) and not lines[end].strip():
        end += 1
    return lines[:start] + lines[end:]


def plan(
    rules: dict[str, Rule],
    replace: bool,
) -> tuple[dict[Rule, list[str]], dict[str, Original], int]:
    """Group the files by rule. Return the groups, the header rewrites and the kept count."""
    groups: dict[Rule, list[str]] = defaultdict(list)
    rewrites: dict[str, Original] = {}
    kept = 0
    for file, rule in sorted(rules.items()):
        if not all(rule):
            continue
        lines = read_lines(file)
        if lines is None or not has_header(lines):
            groups[rule].append(file)
            continue
        stripped = strip_header(lines)
        if stripped is None:
            kept += 1
            if replace:
                print(f"skip {file}: its header is not in a line comment, change it by hand")
        elif replace:
            groups[rule].append(file)
            rewrites[file] = (lines, stripped)
        else:
            kept += 1
    return groups, rewrites, kept


def annotate(
    rule: Rule,
    files: list[str],
    rewrites: dict[str, Original],
) -> int:
    copyrights, licenses = rule
    command = [
        "uvx",
        "reuse",
        "annotate",
        "--exclude-year",
        "--skip-unrecognised",
        "--skip-existing",
        "--template=template",
        "--copyright-prefix=spdx-string-symbol",
    ]
    for copyright_ in copyrights:
        command += ["--copyright", copyright_]
    for identifier in licenses:
        command += ["--license", identifier]
    for file in files:
        if file in rewrites:
            write_lines(
                file,
                rewrites[file][1],
            )
    status = 0
    for start in range(0, len(files), CHUNK):
        chunk = files[start : start + CHUNK]
        status |= subprocess.run(
            [*command, *chunk],
            check=False,
        ).returncode
    # reuse skips file types it does not know, and then the old header must not be lost.
    for file in files:
        if file in rewrites:
            now = read_lines(file)
            if now is None or not has_values(
                now,
                rule,
            ):
                write_lines(
                    file,
                    rewrites[file][0],
                )
                print(f"restored {file}: reuse could not write a header")
                status = 1
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--json",
        type=Path,
        metavar="FILE",
        help="Read a saved reuse lint report.",
    )
    source.add_argument(
        "--toml",
        type=Path,
        metavar="FILE",
        help="Read a REUSE.toml file.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Rewrite the SPDX header of files that have one. Reads REUSE.toml.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Leave out the files that match, for example '**/*.html'. Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan, change nothing.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or folders to limit the run to. The default is every file the rules cover.",
    )
    args = parser.parse_args()
    if args.replace and args.json:
        parser.error("--replace reads REUSE.toml, so it cannot use --json")

    roots = [Path(path).as_posix().removeprefix("./").rstrip("/") or "." for path in args.paths]
    skipped = [glob_to_regex(pattern) for pattern in args.exclude]
    files = [
        file
        for file in project_files()
        if in_roots(
            file,
            roots or ["."],
        )
        and not excluded(file)
        and not any(pattern.fullmatch(file) for pattern in skipped)
    ]

    toml = args.toml or (Path("REUSE.toml") if args.replace else None)
    if toml:
        rules = rules_from_toml(
            toml,
            files,
        )
    else:
        wanted = set(files)
        rules = {
            file: rule
            for file, rule in rules_from_lint(load_report(args.json)).items()
            if file in wanted
        }

    groups, rewrites, kept = plan(
        rules,
        args.replace,
    )
    status = 0
    for rule, group in groups.items():
        copyrights, licenses = rule
        print(f"{len(group)} files: {' | '.join(copyrights)} | {' + '.join(licenses)}", flush=True)
        if args.dry_run:
            for file in group:
                print(f"  {file}{' (replace)' if file in rewrites else ''}")
        else:
            status |= annotate(
                rule,
                group,
                rewrites,
            )
    if not groups:
        print("nothing to annotate")
    if kept and not args.replace:
        print(f"{kept} files already have a header, add --replace to rewrite them")
    return status


if __name__ == "__main__":
    sys.exit(main())
