# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REUSE = (ROOT / "REUSE.toml").read_text(encoding="utf-8")
TEXTS = {path.stem for path in (ROOT / "LICENSES").glob("*.txt")}


def _identifiers() -> set[str]:
    found: set[str] = set()
    for expression in re.findall(
        r'SPDX-License-Identifier\s*=\s*"([^"]+)"',
        REUSE,
    ):
        found.update(
            re.findall(
                r"[A-Za-z0-9.+-]+",
                re.sub(
                    r"\b(AND|OR|WITH)\b",
                    " ",
                    expression,
                ),
            ),
        )
    return found


class TestLicenseLayout:
    def test_the_root_license_is_the_same_text_as_the_apache_text_in_licenses(self):
        assert (ROOT / "LICENSE").read_bytes() == (
            ROOT / "LICENSES" / "Apache-2.0.txt"
        ).read_bytes()

    def test_every_license_in_reuse_toml_has_a_text_in_licenses(self):
        assert _identifiers() - TEXTS == set()

    def test_every_text_in_licenses_is_used_by_reuse_toml(self):
        assert TEXTS - _identifiers() == set()

    def test_the_fonts_and_the_icons_are_not_covered_by_apache_alone(self):
        assert re.search(
            r'IBMPlexSans-Regular-Latin1\.woff".*?SPDX-License-Identifier = "OFL-1\.1-RFN"',
            REUSE,
            flags=re.S,
        )
        assert re.search(
            r'Lilex-Regular\.woff".*?SPDX-License-Identifier = "OFL-1\.1-no-RFN"',
            REUSE,
            flags=re.S,
        )
        assert re.search(
            r'"Apache-2\.0 AND ISC AND MIT"',
            REUSE,
        )

    def test_every_file_that_reuse_toml_names_exists(self):
        named = re.findall(
            r'"([^"*]+\.(?:woff|txt|j2|svg))"',
            REUSE,
        )

        assert named
        assert [path for path in named if not (ROOT / path).exists()] == []

    def test_the_license_field_names_every_license_in_reuse_toml(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        line = next(row for row in pyproject.splitlines() if row.startswith("license ="))
        expression = re.search(
            r'"([^"]+)"',
            line,
        )

        assert expression
        assert set(expression.group(1).split(" AND ")) == _identifiers()

    def test_the_package_ships_the_license_texts(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        line = next(row for row in pyproject.splitlines() if row.startswith("license-files"))

        for pattern in ("LICENSE", "LICENSES/*", "REUSE.toml"):
            assert f'"{pattern}"' in line
