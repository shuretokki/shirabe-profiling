from __future__ import annotations

import polars as pl
import pytest

from shirabe_profiling import ProfileReport


def _outlier_frame() -> pl.DataFrame:
    return pl.DataFrame({"x": [float(i) for i in range(1, 41)] + [1000.0]})


class TestOutliers:
    def test_flags_values_beyond_the_iqr_fences(self):
        rows = ProfileReport(_outlier_frame())._tables.outliers

        assert [row.column for row in rows] == ["x"]
        assert rows[0].count == 1
        assert rows[0].pct == pytest.approx(1 / 41)
        assert rows[0].upper < 1000.0

    def test_skips_columns_without_spread(self):
        df = pl.DataFrame({"x": [5.0] * 30})

        assert ProfileReport(df)._tables.outliers == []

    def test_overview_mode_computes_nothing(self):
        report = ProfileReport(
            _outlier_frame(),
            mode="overview",
        )

        assert report._tables.outliers == []


class TestMissingPatterns:
    def _frame(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "a": [1, None, None, 4, 5, None],
                "b": [1, None, None, 4, 5, 6],
                "c": [None, 2, 3, 4, 5, 6],
            },
        )

    def test_groups_columns_that_are_missing_together(self):
        tables = ProfileReport(self._frame())._tables

        first = tables.missing_patterns[0]
        assert first.columns == ["a", "b"]
        assert first.rows == 2
        assert first.pct == pytest.approx(2 / 6)
        assert tables.complete_rows == 2

    def test_needs_two_columns_with_missing_values(self):
        df = pl.DataFrame({"a": [1, None, 3], "b": [1, 2, 3]})

        assert ProfileReport(df)._tables.missing_patterns == []


class TestReproductionDetails:
    def test_profiling_time_follows_the_mode(self):
        df = pl.DataFrame({"x": [1, 2, 3]})

        keys = list(ProfileReport(df).overview["reproduction"])

        assert keys[keys.index("mode") + 1] == "profiling_time"

    def test_records_thresholds_and_settings(self):
        df = pl.DataFrame({"x": [1, 2, 3]})

        details = ProfileReport(
            df,
            missing_threshold=0.1,
        ).overview["reproduction"]

        assert details["alert.missing_threshold"] == "0.1"
        assert details["display.histogram_bins"] == "50"
        assert details["profiling_time"].endswith(" s")
