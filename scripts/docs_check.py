"""Check that the README code blocks parse and that its local images and links exist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

README = Path("README.md")


def main() -> int:
    text = README.read_text(encoding="utf-8")
    problems: list[str] = []

    blocks = re.findall(
        r"```python\n(.*?)```",
        text,
        flags=re.S,
    )
    for number, block in enumerate(
        blocks,
        start=1,
    ):
        try:
            compile(
                block,
                f"README.md python block {number}",
                "exec",
            )
        except SyntaxError as error:
            problems.append(
                f"python block {number} has a syntax error: {error.msg} (line {error.lineno})",
            )

    targets = re.findall(
        r'(?:src|href)="([^"]+)"',
        text,
    ) + re.findall(
        r"\]\(([^)\s]+)\)",
        text,
    )
    for target in sorted(set(targets)):
        if re.match(
            r"^(https?:|mailto:|#)",
            target,
        ):
            continue
        path = target.split(
            "#",
            1,
        )[0]
        if path and not Path(path).exists():
            problems.append(f"{target} does not exist")

    if problems:
        print("README.md has problems:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"README.md ok: {len(blocks)} python blocks parse, {len(set(targets))} links checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
