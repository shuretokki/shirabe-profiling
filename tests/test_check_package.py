# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "check_package.py"
spec = importlib.util.spec_from_file_location(
    "check_package",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None
check_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_package)


def problems_for(description: str) -> list[str]:
    problems: list[str] = []
    check_package.check_readme(
        SimpleNamespace(description=description),
        problems,
        [],
    )
    return problems


class TestRelativeLinks:
    def test_absolute_and_anchor_links_pass(self):
        description = (
            '<img src="https://example.org/a.png"> [a](https://example.org) <a href="#top">t</a>'
        )

        assert problems_for(description) == []

    @pytest.mark.parametrize(
        "description",
        [
            '<img src="docs/a.png">',
            '<source srcset="docs/a.png">',
            '<a href="CONTRIBUTING.md">c</a>',
            "[c](CONTRIBUTING.md)",
        ],
    )
    def test_a_relative_link_is_a_problem(self, description: str):
        problems = problems_for(description)

        assert len(problems) == 1
        assert "relative link" in problems[0]
