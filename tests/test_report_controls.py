# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from shirabe_profiling import ProfileConfig, ProfileReport


def _numeric(
    columns: int,
    rows: int = 60,
    seed: int = 0,
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    base = rng.normal(size=rows)
    return pl.DataFrame(
        {f"n{i:02d}": base * (i % 3) + rng.normal(size=rows) for i in range(columns)},
    )


def _mixed() -> pl.DataFrame:
    rng = np.random.default_rng(1)
    return pl.DataFrame(
        {
            "a": rng.normal(size=80),
            "b": rng.normal(size=80),
            "c": rng.choice(
                ["x", "y", "z"],
                80,
            ),
            "d": rng.choice(
                ["p", "q"],
                80,
            ),
        },
    )


class TestCorrelationTabOrder:
    def test_most_useful_method_comes_first(self):
        html = ProfileReport(_mixed()).to_html()

        order = [html.index(f'id="tab-corr_{key}"') for key in ("phik", "pearson", "spearman")]
        assert order == sorted(order)

    def test_every_method_is_listed_in_the_chosen_order(self):
        html = ProfileReport(_mixed()).to_html()
        keys = ("phik", "pearson", "spearman", "cramers_v", "kendall")

        positions = [html.index(f'id="tab-corr_{key}"') for key in keys]

        assert positions == sorted(positions)

    def test_the_report_object_keeps_its_own_order(self):
        report = ProfileReport(_mixed())

        assert next(iter(report.correlations)) == "phik"


class TestHeatmapLimit:
    def test_matrix_within_the_limit_has_a_heatmap_and_downloads(self):
        html = ProfileReport(_numeric(5)).to_html()

        assert "reportTheme.mount('corr_pearson'" in html
        assert 'id="corr-save-csv"' in html
        assert 'id="corr-save-png"' in html
        assert 'data-heatmap="corr_pearson"' in html

    def test_larger_matrix_shows_pairs_instead_of_a_heatmap(self):
        config = ProfileConfig(correlation_heatmap_max_columns=4)

        html = ProfileReport(
            _numeric(8),
            config=config,
        ).to_html()

        assert "reportTheme.mount('corr_pearson'" not in html
        assert "This matrix has 8 columns" in html
        assert "no heatmap above 4 columns" in html
        assert "Strongest pairs" in html
        assert 'data-heatmap="corr_pearson"' not in html

    def test_pair_list_is_longer_without_a_heatmap(self):
        config = ProfileConfig(correlation_heatmap_max_columns=4)

        html = ProfileReport(
            _numeric(10),
            config=config,
        ).to_html()

        assert 'id="pairs-corr_pearson" data-limit="10"' in html
        assert "Show 20 more" in html

    def test_default_limit_is_100_columns(self):
        assert ProfileConfig().correlation_heatmap_max_columns == 100

    def test_limit_is_listed_in_the_reproduction_details(self):
        report = ProfileReport(
            _numeric(3),
            correlation_heatmap_max_columns=7,
        )

        assert report.overview["reproduction"]["correlations.heatmap_max_columns"] == "7"
        assert "correlation_heatmap_max_columns=7," in report._call_code

    def test_limit_below_two_is_refused(self):
        with pytest.raises(
            ValueError,
            match="correlation_heatmap_max_columns",
        ):
            ProfileConfig(correlation_heatmap_max_columns=1)


class TestMobileLimits:
    def test_default_limit_for_narrow_screens_is_20_columns(self):
        assert ProfileConfig().correlation_heatmap_max_columns_mobile == 20

    def test_big_matrix_hides_its_heatmap_on_a_narrow_screen_only(self):
        config = ProfileConfig(correlation_heatmap_max_columns_mobile=4)

        html = ProfileReport(
            _numeric(8),
            config=config,
        ).to_html()

        assert "reportTheme.mount('corr_pearson'" in html
        assert 'class="heatmap-wrap"' in html
        assert "data-mobile-hidden" in html
        assert "A narrow screen shows no heatmap above 4 columns" in html

    def test_small_matrix_keeps_its_heatmap_on_a_narrow_screen(self):
        html = ProfileReport(_numeric(5)).to_html()

        assert "data-mobile-hidden" not in html.split("<body>")[1]
        assert "A narrow screen shows no heatmap" not in html

    def test_hidden_heatmap_comes_with_a_longer_pair_list(self):
        config = ProfileConfig(correlation_heatmap_max_columns_mobile=4)

        html = ProfileReport(
            _numeric(10),
            config=config,
        ).to_html()

        assert "Show 20 more" in html

    def test_limit_is_listed_in_the_reproduction_details(self):
        report = ProfileReport(
            _numeric(3),
            correlation_heatmap_max_columns_mobile=9,
        )

        reproduction = report.overview["reproduction"]
        assert reproduction["correlations.heatmap_max_columns_mobile"] == "9"

    def test_limit_below_two_is_refused(self):
        with pytest.raises(
            ValueError,
            match="correlation_heatmap_max_columns_mobile",
        ):
            ProfileConfig(correlation_heatmap_max_columns_mobile=1)

    def test_guide_names_both_limits(self):
        html = ProfileReport(_numeric(3)).to_html()

        assert "more than 100 columns shows its strongest pairs" in html
        assert "the limit is 20 columns" in html


class TestNarrowTabs:
    def test_target_tabs_keep_their_name_for_icon_only_view(self):
        html = ProfileReport(
            pl.DataFrame({"y": [0, 1] * 30, "x": range(60)}),
            target="y",
        ).to_html()

        assert 'title="Link to target" aria-label="Link to target"' in html

    def test_compact_cells_bar_has_vertical_room(self):
        css = ProfileReport(_mixed()).to_html()

        assert "padding: 0.25rem 0.5rem;" in css


class TestShowMore:
    def test_long_variables_table_starts_with_ten_rows(self):
        html = ProfileReport(_numeric(20)).to_html()

        assert 'id="variables-body" data-limit="10"' in html
        assert 'data-limit-toggle="variables-body"' in html
        assert "Show 10 more" in html

    def test_short_variables_table_shows_every_row(self):
        html = ProfileReport(_numeric(15)).to_html()

        assert 'id="variables-body">' in html
        assert 'data-limit-toggle="variables-body"' not in html

    def test_long_alert_group_gets_a_button_with_the_rest_count(self):
        df = pl.DataFrame({f"c{i:02d}": [None] * 30 + [1.0] * 30 for i in range(15)})

        html = ProfileReport(df).to_html()

        assert 'class="alert-items" id="alert-items-' in html
        assert 'data-limit="8"' in html
        assert "Show 7 more" in html

    def test_short_alert_group_has_no_button(self):
        df = pl.DataFrame({f"c{i}": [None] * 30 + [1.0] * 30 for i in range(3)})

        html = ProfileReport(df).to_html()

        assert 'data-limit="8"' not in html
        assert 'data-limit-toggle="alert-items' not in html

    def test_lists_that_hid_rows_on_the_server_now_use_the_same_rule(self):
        assert "data-more" not in ProfileReport(_numeric(4)).to_html()


class TestDownloads:
    def test_chart_titles_name_the_column(self):
        html = ProfileReport(_mixed()).to_html()

        assert "a's Distribution" in html
        assert "c's Top Values" in html

    def test_compact_cells_is_an_icon_button_on_the_right(self):
        html = ProfileReport(_mixed()).to_html()

        assert 'class="tab-bar-tools"' in html
        assert 'data-truncate-target="sample-panel" aria-pressed="true"' in html
        assert 'class="switch-input"' not in html

    def test_chart_download_uses_the_save_icon(self):
        html = ProfileReport(_mixed()).to_html()

        assert html.count("data-save-png=") >= 3
        assert "Download chart as image" in html

    def test_column_chart_has_an_image_button(self):
        html = ProfileReport(_mixed()).to_html()

        assert 'data-save-png="col_chart_0"' in html
        assert 'data-name="a"' in html

    def test_interactions_plot_has_an_image_button(self):
        html = ProfileReport(_mixed()).to_html()

        assert 'data-save-png="interact-chart"' in html
        assert 'data-name-from="interact-x,interact-y"' in html

    def test_sample_has_a_csv_button(self):
        html = ProfileReport(_mixed()).to_html()

        assert 'data-save-table="sample-panel"' in html


class TestNotebookFrame:
    @staticmethod
    def _script(html: str) -> str:
        start = html.index("window.frameElement")
        return html[
            html.rindex(
                "<script>",
                0,
                start,
            ) : html.index(
                "</script>",
                start,
            )
        ]

    def test_the_report_fits_the_marimo_frame_to_the_current_tab(self):
        script = self._script(ProfileReport(_mixed()).to_html())

        assert "__resizeIframe" in script
        assert "document.body.offsetHeight" in script
        assert "frame.style.height" in script
        assert "'reportshown'" in script
        assert "ResizeObserver" in script

    def test_a_frame_that_is_not_marimo_is_left_alone(self):
        script = self._script(ProfileReport(_mixed()).to_html())

        assert "if (!frame ||" in script
        assert "return;" in script
        assert script.index("indexOf('__resizeIframe') === -1") < script.index("function fit")

    def test_a_page_that_is_not_framed_or_cannot_reach_its_frame_does_nothing(self):
        script = self._script(ProfileReport(_mixed()).to_html())

        assert "try { frame = window.frameElement; } catch (err) { return; }" in script
