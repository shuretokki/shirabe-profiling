# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

import polars as pl

from shirabe_profiling import ProfileConfig, ProfileReport
from shirabe_profiling.reproduction import describe_call

if TYPE_CHECKING:
    from pathlib import Path


class TestDescribeCall:
    def test_default_call(self):
        code = describe_call(pl.DataFrame({"x": [1]}))

        assert code.splitlines() == [
            "from shirabe_profiling import ProfileReport",
            "",
            "report = ProfileReport(",
            "    df,  # your Polars DataFrame",
            ")",
            'report.to_html("report.html")',
        ]

    def test_shows_the_arguments_the_user_passed(self):
        code = describe_call(
            pl.DataFrame({"x": [1]}),
            title="Sales",
            mode="overview",
            kwargs={"missing_threshold": 0.1},
        )

        assert "    title='Sales'," in code
        assert "    mode='overview'," in code
        assert "    missing_threshold=0.1," in code

    def test_a_config_object_replaces_the_loose_arguments(self):
        config = ProfileConfig(
            title="Sales",
            histogram_bins=20,
        )

        code = describe_call(
            pl.DataFrame({"x": [1]}),
            config=config,
        )

        assert "from shirabe_profiling import ProfileConfig, ProfileReport" in code
        assert "    config=ProfileConfig(" in code
        assert "        histogram_bins=20," in code
        assert "missing_threshold" not in code

    def test_an_untouched_config_object_stays_short(self):
        code = describe_call(
            pl.DataFrame({"x": [1]}),
            config=ProfileConfig(),
        )

        assert "    config=ProfileConfig()," in code

    def test_a_file_path_is_reduced_to_its_name(self):
        code = describe_call("/home/someone/private/sales.csv")

        assert "'sales.csv'," in code
        assert "/home/someone" not in code

    def test_other_source_types(self):
        assert "lf,  # your Polars LazyFrame" in describe_call(pl.LazyFrame({"x": [1]}))
        assert "your pandas DataFrame" in describe_call(_FakePandas())
        assert "data,  # your dict" in describe_call({"x": [1]})


class _FakePandas:
    __module__ = "pandas.core.frame"


class TestReportUsesTheRealCall:
    def test_html_shows_how_the_report_was_called(self):
        df = pl.DataFrame({"x": [1, 2, 3]})

        html = ProfileReport(
            df,
            title="Sales",
            missing_threshold=0.1,
        ).to_html()

        assert "title='Sales'," in unquote(html)
        assert "missing_threshold=0.1," in unquote(html)

    def test_html_keeps_a_file_path_private(self, tmp_path: Path):
        path = tmp_path / "sales.csv"
        pl.DataFrame({"x": [1, 2, 3]}).write_csv(path)

        html = ProfileReport(path).to_html()

        assert "sales.csv" in unquote(html)
        assert str(tmp_path) not in unquote(html)
