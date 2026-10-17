# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("src", "tests", "scripts")
ROOT_FILES = ("pyproject.toml", "REUSE.toml", "cliff.toml", "flake.nix")
TOOL_COMMENT = re.compile(
    r"^(?:SPDX-|REUSE-|noqa|type:|pragma|fmt:|ruff:|pyright:|basedpyright:|https?://)",
)


def _python_comments(text: str) -> list[tuple[int, str]]:
    return [
        (token.start[0], token.string.lstrip("#").strip())
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type == tokenize.COMMENT
    ]


def _hash_comments(text: str) -> list[tuple[int, str]]:
    return [
        (number, line.strip().lstrip("#").strip())
        for number, line in enumerate(text.splitlines(), 1)
        if line.strip().startswith("#")
    ]


def _css_comments(text: str) -> list[tuple[int, str]]:
    return [
        (
            text.count(
                "\n",
                0,
                match.start(),
            )
            + 1,
            match.group(1).strip(),
        )
        for match in re.finditer(
            r"/\*(.*?)\*/",
            text,
            re.S,
        )
    ]


def _comments(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        return _python_comments(text)
    if path.suffix == ".css":
        return _css_comments(text)
    return _hash_comments(text)


def _files() -> list[Path]:
    found = [
        path
        for folder in FOLDERS
        for pattern in ("*.py", "*.css")
        for path in (ROOT / folder).rglob(pattern)
    ]
    return sorted(found + [ROOT / name for name in ROOT_FILES if (ROOT / name).exists()])


class TestComments:
    def test_every_comment_starts_with_a_lowercase_letter(self):
        loud = [
            f"{path.relative_to(ROOT)}:{number}: {body[:60]}"
            for path in _files()
            for number, body in _comments(path)
            if body and not TOOL_COMMENT.match(body) and body[0].isupper()
        ]

        assert loud == []

    def test_the_check_sees_the_comments_of_every_kind_of_file(self):
        suffixes = {path.suffix for path in _files()}

        assert {".py", ".css", ".toml"} <= suffixes
