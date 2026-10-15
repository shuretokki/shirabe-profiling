"""Add trailing commas so that ruff format puts each argument on its own line.

A call or a function signature with two or more arguments gets a trailing comma
when it sits on one line. ruff format keeps the comma and splits the line.
List, set, and dict literals are left alone.

Run "just commas" to add the commas. "just check" runs this script with --check.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import io
import sys
import tokenize
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

BUILTIN_NAMES = frozenset(dir(builtins))
SELF_NAMES = ("self", "cls")

Spot = tuple[int, int]


def find_spots(
    source: str,
    min_args: int = 2,
) -> list[Spot]:
    """Return the line and column where each missing comma goes. Lines start at 1."""
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    spots = [
        *_call_spots(
            tree,
            lines,
            min_args,
        ),
        *_signature_spots(
            source,
            tree,
            lines,
            min_args,
        ),
    ]
    return sorted(set(spots))


def add_commas(
    source: str,
    spots: list[Spot],
) -> str:
    """Insert a comma at each spot."""
    lines = source.splitlines(keepends=True)
    for row, column in sorted(set(spots), reverse=True):
        text = lines[row - 1]
        lines[row - 1] = text[:column] + "," + text[column:]
    return "".join(lines)


def _comma_column(
    text: str,
    closer_column: int,
) -> int | None:
    """Return the column for the comma, or None when the call needs no comma."""
    if closer_column >= len(text) or text[closer_column] != ")":
        return None
    before = text[:closer_column].rstrip()
    if before.endswith(","):
        return None
    return len(before)


def _character_column(
    text: str,
    byte_column: int,
) -> int:
    return len(text.encode()[:byte_column].decode())


def _call_spots(
    node: ast.AST,
    lines: list[str],
    min_args: int,
) -> Iterator[Spot]:
    if isinstance(node, ast.JoinedStr):
        return
    if (
        isinstance(node, ast.Call)
        and node.end_lineno == node.lineno
        and node.end_col_offset is not None
    ):
        arguments = len(node.args) + len(node.keywords)
        is_builtin = isinstance(node.func, ast.Name) and node.func.id in BUILTIN_NAMES
        if arguments >= min_args and not is_builtin:
            text = lines[node.lineno - 1]
            closer = (
                _character_column(
                    text,
                    node.end_col_offset,
                )
                - 1
            )
            column = _comma_column(
                text,
                closer,
            )
            if column is not None:
                yield node.lineno, column
    for child in ast.iter_child_nodes(node):
        yield from _call_spots(
            child,
            lines,
            min_args,
        )


def _signature_spots(
    source: str,
    tree: ast.AST,
    lines: list[str],
    min_args: int,
) -> Iterator[Spot]:
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        spec = node.args
        params = [*spec.posonlyargs, *spec.args, *spec.kwonlyargs]
        if spec.vararg:
            params.append(spec.vararg)
        if spec.kwarg:
            params.append(spec.kwarg)
        if params and params[0].arg in SELF_NAMES:
            params = params[1:]
        if len(params) < min_args:
            continue
        spot = _signature_spot(
            tokens,
            lines,
            node,
        )
        if spot is not None:
            yield spot


def _signature_spot(
    tokens: list[tokenize.TokenInfo],
    lines: list[str],
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Spot | None:
    start = next(
        (
            index
            for index, token in enumerate(tokens)
            if token.type == tokenize.NAME
            and token.string == node.name
            and token.start[0] == node.lineno
            and tokens[index - 1].string == "def"
        ),
        None,
    )
    if start is None or tokens[start + 1].string != "(":
        return None

    depth = 0
    for token in tokens[start + 1 :]:
        if token.type != tokenize.OP:
            continue
        if token.string in "([{":
            depth += 1
        elif token.string in ")]}":
            depth -= 1
        if depth == 0:
            row, column = token.start
            if row != node.lineno:
                return None
            comma = _comma_column(
                lines[row - 1],
                column,
            )
            return None if comma is None else (row, comma)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add trailing commas so that ruff format splits each argument onto a line.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="List the missing commas and exit with 1, without changing files.",
    )
    parser.add_argument(
        "--min-args",
        type=int,
        default=2,
    )
    args = parser.parse_args(argv)

    total = 0
    for root in args.paths:
        for path in sorted(root.rglob("*.py")) if root.is_dir() else [root]:
            source = path.read_text(encoding="utf-8")
            spots = find_spots(
                source,
                args.min_args,
            )
            total += len(spots)
            if args.check:
                lines = source.splitlines()
                for row, _ in spots:
                    print(f"{path}:{row}: {lines[row - 1].strip()}")
            elif spots:
                path.write_text(
                    add_commas(
                        source,
                        spots,
                    ),
                    encoding="utf-8",
                )

    if args.check:
        if total:
            print(f"{total} missing trailing commas. Run: just commas")
        return 1 if total else 0
    print(f"{total} commas added")
    return 0


if __name__ == "__main__":
    sys.exit(main())
