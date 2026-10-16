# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import polars as pl

from shirabe_profiling import ProfileConfig, ProfileReport
from shirabe_profiling.dataset_overview import compute_overview


def _overview(
    df: pl.DataFrame,
    config: ProfileConfig | None = None,
):
    return compute_overview(
        df,
        {},
        config,
    )


def _numbered(rows: int) -> pl.DataFrame:
    return pl.DataFrame({"n": list(range(rows)), "t": [f"r{i}" for i in range(rows)]})


class TestRandomSample:
    def test_draws_ten_rows_in_their_original_order(self):
        overview = _overview(_numbered(100))

        numbers = [int(row["n"]) for row in overview.sample_random]

        assert len(numbers) == 10
        assert numbers == sorted(numbers)

    def test_the_draw_repeats_with_the_same_seed(self):
        first = _overview(_numbered(100)).sample_random
        second = _overview(_numbered(100)).sample_random

        assert first == second

    def test_a_different_seed_gives_other_rows(self):
        first = _overview(_numbered(100)).sample_random
        other = _overview(
            _numbered(100),
            ProfileConfig(interaction_sample_seed=7),
        ).sample_random

        assert first != other

    def test_small_data_has_no_random_sample(self):
        assert _overview(_numbered(20)).sample_random == []

    def test_overview_mode_has_no_random_sample(self):
        overview = _overview(
            _numbered(100),
            ProfileConfig(mode="overview"),
        )

        assert overview.sample_random == []


class TestMostMissing:
    @staticmethod
    def _df() -> pl.DataFrame:
        return pl.DataFrame(
            {
                "a": [1, None, None, 4, None, 6],
                "b": [1, 2, None, 4, 5, 6],
                "c": [1, None, None, 4, 5, 6],
            },
        )

    def test_rows_with_more_gaps_come_first(self):
        overview = _overview(self._df())

        assert [row["a"] for row in overview.sample_most_missing[:2]] == [None, None]
        assert overview.sample_most_missing[0]["c"] is None
        assert overview.sample_most_missing[0]["b"] is None

    def test_ties_keep_the_file_order(self):
        overview = _overview(self._df())

        assert [row["b"] for row in overview.sample_most_missing] == [None, "2", "5"]

    def test_the_count_is_the_rows_with_any_gap(self):
        assert _overview(self._df()).rows_with_missing == 3

    def test_rows_without_gaps_are_left_out(self):
        overview = _overview(self._df())

        assert len(overview.sample_most_missing) == 3

    def test_complete_data_has_no_tab(self):
        overview = _overview(_numbered(30))

        assert overview.sample_most_missing == []
        assert overview.rows_with_missing == 0

    def test_overview_mode_skips_it(self):
        overview = _overview(
            self._df(),
            ProfileConfig(mode="overview"),
        )

        assert overview.sample_most_missing == []
        assert overview.rows_with_missing == 0


class TestSampleTabs:
    def test_tabs_appear_in_a_complete_report(self):
        df = _numbered(100).with_columns(
            pl.when(pl.col("n") % 7 == 0).then(None).otherwise(pl.col("t")).alias("t"),
        )

        html = ProfileReport(df).to_html()

        assert 'id="tab-sample-random"' in html
        assert 'id="tab-sample-missing"' in html
        assert html.index('id="tab-sample-tail"') < html.index('id="tab-sample-random"')
        assert html.index('id="tab-sample-random"') < html.index('id="tab-sample-missing"')

    def test_no_extra_tabs_for_small_complete_data(self):
        html = ProfileReport(_numbered(12)).to_html()

        assert 'id="tab-sample-random"' not in html
        assert 'id="tab-sample-missing"' not in html

    def test_overview_mode_keeps_head_and_tail_only(self):
        html = ProfileReport(
            _numbered(100),
            mode="overview",
        ).to_html()

        assert 'id="tab-sample-head"' in html
        assert 'id="tab-sample-random"' not in html
