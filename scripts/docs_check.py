# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Check that the README code blocks parse and that its local images and links exist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

README = Path("README.md")
RAW_IMAGE = re.compile(r"^https://raw\.githubusercontent\.com/[^/]+/[^/]+/main/(.+)$")
OUTSIDE = re.compile(r"^(https?:|mailto:|#)")


def python_blocks(text: str) -> list[str]:
    return re.findall(
        r"```python\n(.*?)```",
        text,
        flags=re.S,
    )


def link_targets(text: str) -> list[str]:
    attributes = re.findall(
        r'(?:src|href|srcset)="([^"]+)"',
        text,
    )
    return sorted(
        set(
            attributes
            + re.findall(
                r"\]\(([^)\s]+)\)",
                text,
            ),
        ),
    )


def check_blocks(blocks: list[str]) -> list[str]:
    problems = []
    for number, block in enumerate(blocks, start=1):
        try:
            compile(block, f"README.md python block {number}", "exec")
        except SyntaxError as error:
            problems.append(
                f"python block {number} has a syntax error: {error.msg} (line {error.lineno})",
            )
    return problems


def check_target(target: str) -> str | None:
    """Return a problem for one link, or None when it is fine."""
    raw = RAW_IMAGE.match(target)
    if raw:
        # The README uses raw URLs, because PyPI cannot show a relative image.
        found = Path(raw.group(1)).exists()
        return (
            None if found else f"{target} points to {raw.group(1)}, which is not in this checkout"
        )
    if OUTSIDE.match(target):
        return None
    path = target.split(
        "#",
        1,
    )[0]
    return f"{target} does not exist" if path and not Path(path).exists() else None


def main() -> int:
    text = README.read_text(encoding="utf-8")
    blocks = python_blocks(text)
    targets = link_targets(text)
    problems = check_blocks(blocks)
    problems += [problem for target in targets if (problem := check_target(target))]

    if problems:
        print("README.md has problems:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"README.md ok: {len(blocks)} python blocks parse, {len(targets)} links checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
