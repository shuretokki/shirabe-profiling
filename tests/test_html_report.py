# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re

import numpy as np
import polars as pl

from shirabe_profiling.alerts import check_quality
from shirabe_profiling.analyzers import analyze
from shirabe_profiling.config import ProfileConfig
from shirabe_profiling.correlations import compute_correlations
from shirabe_profiling.dataset_overview import compute_overview
from shirabe_profiling.report.html import render_html
from shirabe_profiling.tables import compute_tables
from shirabe_profiling.type_inference import infer_types


def _render(
    df: pl.DataFrame,
    config: ProfileConfig | None = None,
) -> str:
    config = config or ProfileConfig()
    column_types = infer_types(
        df,
        config,
    )
    column_stats = analyze(
        df,
        column_types,
        config,
    )
    overview = compute_overview(
        df,
        column_types,
        config,
    )
    alerts = check_quality(
        column_stats,
        overview,
        config,
    )
    correlations = compute_correlations(
        df,
        column_types,
        config,
    )
    return render_html(
        title=config.title,
        version="0.1.0",
        overview=overview,
        column_stats=column_stats,
        alerts=alerts,
        correlations=correlations,
        tables=compute_tables(
            df,
            column_stats,
            config,
        ),
        config=config,
    )


class TestRenderBasic:
    def test_returns_html_string(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_contains_title(self, mixed_df: pl.DataFrame):
        html = _render(
            mixed_df,
            ProfileConfig(title="Test Report"),
        )
        assert "Test Report" in html

    def test_contains_overview_cards(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "Dataset Overview" in html
        assert "Rows" in html
        assert "Columns" in html
        assert "Missing Cells" in html

    def test_contains_column_tabs(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "Column Details" in html
        assert "age" in html
        assert "salary" in html
        assert "city" in html

    def test_contains_echarts(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "echarts.init" in html

    def test_contains_footer(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "shirabe-profiling" in html


class TestRenderAlerts:
    def test_alerts_section_present(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "Alerts" in html

    def test_no_alerts_section_when_clean(self):
        df = pl.DataFrame({"a": list(range(100)), "b": list(range(100))})
        config = ProfileConfig(
            missing_threshold=1.0,
            duplicate_threshold=1.0,
        )
        html = _render(
            df,
            config,
        )
        assert "alert_type" not in html.lower() or "Alerts" in html


class TestRenderCorrelations:
    def test_correlation_heatmaps(self, numeric_df: pl.DataFrame):
        html = _render(numeric_df)
        assert "Correlations" in html
        assert "corr_pearson" in html
        assert "corr_spearman" in html
        assert "corr_kendall" in html
        assert "heatmap" in html

    def test_tab_buttons(self, numeric_df: pl.DataFrame):
        html = _render(numeric_df)
        assert 'id="corr-tabs"' in html
        assert "Pearson" in html
        assert "Spearman" in html
        assert "Kendall" in html
        assert 'aria-controls="panel-corr_pearson"' in html

    def test_tab_panels(self, numeric_df: pl.DataFrame):
        html = _render(numeric_df)
        assert "panel-corr_pearson" in html
        assert "panel-corr_spearman" in html
        assert "panel-corr_kendall" in html

    def test_first_tab_active(self, numeric_df: pl.DataFrame):
        html = _render(numeric_df)
        assert 'id="tab-corr_phik" aria-controls="panel-corr_phik" aria-selected="true"' in html
        pearson_tab = 'id="tab-corr_pearson" aria-controls="panel-corr_pearson"'
        assert f'{pearson_tab} aria-selected="false"' in html
        assert 'aria-labelledby="tab-corr_pearson" hidden>' in html

    def test_cramers_v_tab(self, categorical_df: pl.DataFrame):
        html = _render(categorical_df)
        assert "corr_cramers_v" in html
        assert "Cramers V" in html
        assert "panel-corr_cramers_v" in html

    def test_categorical_only_no_numeric_tabs(self, categorical_df: pl.DataFrame):
        html = _render(categorical_df)
        assert "corr_pearson" not in html
        assert "corr_cramers_v" in html

    def test_mixed_has_all_tabs(self):
        df = pl.DataFrame(
            {
                "n1": [1, 2, 3, 4, 5],
                "n2": [5, 4, 3, 2, 1],
                "c1": ["a", "b", "a", "b", "a"],
                "c2": ["x", "y", "x", "y", "x"],
            },
        )
        html = _render(df)
        assert "corr_pearson" in html
        assert "corr_cramers_v" in html
        assert "corr_phik" in html

    def test_phik_tab_present(self, numeric_df: pl.DataFrame):
        html = _render(numeric_df)
        assert "corr_phik" in html
        assert "Phik" in html
        assert "panel-corr_phik" in html

    def test_no_correlation_single_numeric(self):
        df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        html = _render(df)
        assert "corr_pearson" not in html
        assert "corr_cramers_v" not in html
        assert 'id="corr-tabs"' not in html

    def test_no_correlation_overview_mode(self, numeric_df: pl.DataFrame):
        html = _render(
            numeric_df,
            ProfileConfig(mode="overview"),
        )
        assert "corr_pearson" not in html
        assert 'id="corr-tabs"' not in html


class TestRenderCharts:
    def test_numeric_histogram(self, numeric_df: pl.DataFrame):
        html = _render(numeric_df)
        assert "Distribution" in html

    def test_categorical_bar(self, categorical_df: pl.DataFrame):
        html = _render(categorical_df)
        assert "Top Values" in html

    def test_boolean_pie(self, boolean_df: pl.DataFrame):
        html = _render(boolean_df)
        assert "True" in html
        assert "False" in html


class TestRenderCategoricalOther:
    def _truncated_df(self) -> pl.DataFrame:
        return pl.DataFrame({"cat": ["a"] * 5 + ["b"] * 4 + ["c"] * 3 + ["d"] * 2 + ["e"] * 1})

    def test_other_bar_in_chart_when_truncated(self):
        from shirabe_profiling.analyzers import CategoricalStats, OtherValues
        from shirabe_profiling.report.charts import EChartsRenderer
        from shirabe_profiling.report.html import _chart_for_column
        from shirabe_profiling.type_inference import ColumnType

        stats = CategoricalStats(
            column_name="cat",
            column_type=ColumnType.CATEGORICAL,
            count=15,
            missing_count=0,
            missing_pct=0.0,
            top_values=[{"value": "a", "count": 5}, {"value": "b", "count": 4}],
            other_values=OtherValues(
                count=6,
                distinct_remaining=3,
            ),
        )
        html = _chart_for_column(
            stats,
            EChartsRenderer(),
            idx=0,
            name="col",
        )
        assert '"Other"' in html
        assert "6" in html

    def test_other_absent_from_chart_when_no_tail(self):
        from shirabe_profiling.analyzers import CategoricalStats
        from shirabe_profiling.report.charts import EChartsRenderer
        from shirabe_profiling.report.html import _chart_for_column
        from shirabe_profiling.type_inference import ColumnType

        stats = CategoricalStats(
            column_name="cat",
            column_type=ColumnType.CATEGORICAL,
            count=6,
            missing_count=0,
            missing_pct=0.0,
            top_values=[{"value": "a", "count": 3}, {"value": "b", "count": 3}],
            other_values=None,
        )
        html = _chart_for_column(
            stats,
            EChartsRenderer(),
            idx=0,
            name="col",
        )
        assert '"Other"' not in html

    def test_other_stats_rows_in_report(self):
        html = _render(
            self._truncated_df(),
            ProfileConfig(n_top_values=2),
        )
        assert "Other (rows)" in html
        assert "Remaining categories" in html

    def test_other_stats_absent_when_no_tail(self):
        df = pl.DataFrame({"cat": ["a", "b", "c"] * 4})
        html = _render(
            df,
            ProfileConfig(n_top_values=10),
        )
        assert "Other (rows)" not in html
        assert "Remaining categories" not in html


class TestMissingInVariables:
    def test_missing_cell_shows_count_and_share(self):
        df = pl.DataFrame({"a": [1, None, 3, 4], "b": ["x", "y", "z", "w"]})
        html = _render(df)
        start = html.index('id="variables-section"')
        section = html[
            start : html.index(
                "</section>",
                start,
            )
        ]
        assert "1 (25.0%)" in section
        assert "0 (0.0%)" in section

    def test_missing_cell_sorts_by_count(self):
        df = pl.DataFrame({"a": [1, None, None, 4]})
        html = _render(df)
        assert 'data-value="2"><span>2 (50.0%)' in html

    def test_overview_has_no_missing_panel(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="missing-panel"' not in html
        assert "Missing Cells" in html


class TestRenderSampleSection:
    def test_sample_section_present(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "Sample" in html
        assert "sample-head" in html
        assert "sample-tail" in html

    def test_head_tail_tabs(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'aria-controls="panel-sample-tail"' in html


class TestRenderDuplicateSection:
    def test_duplicate_section_with_dupes(self):
        df = pl.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        html = _render(df)
        assert "Duplicate Rows" in html
        assert html.count("Duplicate Rows") >= 2

    def test_no_duplicate_section_without_dupes(self):
        df = pl.DataFrame({"a": [1, 2, 3]})
        html = _render(df)
        assert html.count("Duplicate Rows") == 1


class TestRenderReproduction:
    def test_reproduction_section(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "Reproduction Details" in html
        assert "polars_version" in html
        assert "shirabe_profiling_version" in html


class TestRenderEdgeCases:
    def test_empty_dataframe(self, empty_df: pl.DataFrame):
        html = _render(empty_df)
        assert "<!DOCTYPE html>" in html
        assert "0" in html

    def test_single_column(self):
        df = pl.DataFrame({"x": [1, 2, 3]})
        html = _render(df)
        assert "<!DOCTYPE html>" in html
        assert "x" in html


class TestFilters:
    def test_format_number(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "10" in html  # n_rows

    def test_format_pct(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "%" in html


class TestAlertValueFormat:
    @staticmethod
    def _alert(
        alert_type: str,
        value: float,
    ) -> dict:
        return {"column": "x", "alert_type": alert_type, "value": value, "details": {}}

    def test_share_alerts_are_percentages(self):
        from shirabe_profiling.report.html import _format_alert_value

        assert (
            _format_alert_value(
                self._alert(
                    "HIGH_MISSING",
                    0.143,
                ),
            )
            == "14.3%"
        )
        assert (
            _format_alert_value(
                self._alert(
                    "IMBALANCED",
                    0.95,
                ),
            )
            == "95.0%"
        )

    def test_skew_and_correlation_are_plain_numbers(self):
        from shirabe_profiling.report.html import _format_alert_value

        assert (
            _format_alert_value(
                self._alert(
                    "SKEWED",
                    3.2,
                ),
            )
            == "3.20"
        )
        assert (
            _format_alert_value(
                self._alert(
                    "HIGH_CORRELATION",
                    0.853,
                ),
            )
            == "0.85"
        )

    def test_uniform_shows_p_value(self):
        from shirabe_profiling.report.html import _format_alert_value

        assert (
            _format_alert_value(
                self._alert(
                    "UNIFORM",
                    0.12,
                ),
            )
            == "p = 0.120"
        )

    def test_constant_shows_distinct_count(self):
        from shirabe_profiling.report.html import _format_alert_value

        assert (
            _format_alert_value(
                self._alert(
                    "CONSTANT",
                    1.0,
                ),
            )
            == "1 distinct"
        )


class TestPagesAndHeader:
    def test_page_tabs(self, mixed_df: pl.DataFrame):
        html = _render(
            mixed_df,
            ProfileConfig(title="My Data"),
        )
        assert 'id="tab-page-report"' in html
        assert 'id="tab-page-guide"' in html
        assert 'id="page-guide"' in html
        assert "Reading the report" in html

    def test_guide_page_starts_hidden(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'aria-labelledby="tab-page-guide" class="space-y-6" hidden' in html

    def test_header_lists_no_dataset_facts(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        header = html[html.index('<header class="app-header"') : html.index("</header>")]
        assert "Rows" not in header
        assert "header-facts" not in header


class TestVariablesSection:
    def test_variables_table_is_sortable(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="variables-section"' in html
        assert "data-sortable" in html
        assert 'data-open-column="0"' in html

    def test_one_row_per_column(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index('id="variables-section"')
        section = html[
            start : html.index(
                "</section>",
                start,
            )
        ]
        assert section.count("data-open-column=") == mixed_df.width


class TestOutlierAndPatternSections:
    def test_outlier_section_when_values_are_extreme(self):
        df = pl.DataFrame({"x": [float(i) for i in range(1, 41)] + [1000.0]})
        html = _render(df)
        assert 'id="outliers-section"' in html

    def test_outliers_are_a_table_that_scrolls_sideways(self):
        df = pl.DataFrame({"x": [float(i) for i in range(1, 41)] + [1000.0]})
        html = _render(df)
        section = html[html.index('id="outliers-section"') :]
        section = section[: section.index("</section>")]
        assert 'class="overflow-x-auto"' in section
        assert 'class="table table-outliers"' in section
        assert "<ul" not in section

    def test_outliers_and_patterns_have_no_description(self):
        df = pl.DataFrame(
            {
                "x": [float(i) for i in range(1, 41)] + [1000.0],
                "a": ([1, None, None, 4, 5, None] * 7)[:41],
                "b": ([1, None, None, 4, 5, 6] * 7)[:41],
            },
        )
        html = _render(df)
        for marker in ('id="outliers-section"', 'id="patterns-section"'):
            section = html[html.index(marker) :]
            section = section[: section.index("</section>")]
            assert "small muted p-3" not in section

    def test_no_outlier_section_when_clean(self):
        df = pl.DataFrame({"x": [float(i) for i in range(1, 41)]})
        html = _render(df)
        assert 'id="outliers-section"' not in html

    def test_pattern_section_for_columns_missing_together(self):
        df = pl.DataFrame(
            {
                "a": [1, None, None, 4, 5, None],
                "b": [1, None, None, 4, 5, 6],
                "c": [None, 2, 3, 4, 5, 6],
            },
        )
        html = _render(df)
        assert 'id="patterns-section"' in html

    def test_overview_mode_hides_both_sections(self):
        df = pl.DataFrame({"x": [float(i) for i in range(1, 41)] + [1000.0]})
        html = _render(
            df,
            ProfileConfig(mode="overview"),
        )
        assert 'id="outliers-section"' not in html
        assert 'id="patterns-section"' not in html


class TestReproductionText:
    def test_text_block_is_the_only_layout(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="reproduction-text"' in html
        assert 'data-layout-choice="text"' not in html

    def test_lists_alert_thresholds_and_environment(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "alert.missing_threshold: 0.05" in html
        assert "python_version:" in html
        assert "interactions.sample_seed: 42" in html


class TestAlertsLayout:
    def test_alerts_are_grouped_only(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'class="alert-groups"' in html
        assert 'data-layout-choice="table"' not in html
        assert 'aria-label="Alerts layout"' not in html


class TestHeaderActionsAndGuide:
    def test_source_link_lives_in_the_header(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        header = html[html.index('<header class="app-header"') : html.index("</header>")]
        assert 'href="https://github.com/shuretokki/shirabe-profiling"' in header

    def test_no_footer(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "<footer" not in html

    def test_settings_menu_offers_theme_and_density(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="settings-menu"' in html
        for value in ("system", "dark", "light"):
            assert f'data-setting="theme" data-value="{value}"' in html
        for value in ("auto", "default", "touch"):
            assert f'data-setting="density" data-value="{value}"' in html

    def test_theme_is_applied_before_the_styles(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert html.index("window.reportSettings") < html.index("<style>")

    def test_palette_choice_is_gone_and_dark_is_charcoal(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'data-setting="palette"' not in html
        assert "data-palette" not in html
        assert "palette-label" not in html
        assert "--editor: #1a1a1a;" in html
        assert "--surface: #242424;" in html
        assert "--text: #d4d4d4;" in html
        assert "#092728;\n  --surface" not in html

    def test_diagnostics_do_not_list_a_palette(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "'palette: '" not in html

    def test_guide_terms_link_out(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index('id="page-guide"')
        guide = html[
            start : html.index(
                "</main>",
                start,
            )
        ]
        assert guide.count('target="_blank" rel="noopener"') >= 10
        assert "wikipedia.org/wiki/Skewness" in guide

    def test_guide_has_no_keyboard_section(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert "guide-keyboard" not in html
        assert "Keyboard" not in html

    def test_guide_sections_do_not_repeat_each_other(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index('id="page-guide"')
        guide = html[start : html.index('id="page-feedback"')]
        assert "guide-terms" not in guide
        assert guide.count("wikipedia.org/wiki/P-value") == 1
        assert guide.count('wikipedia.org/wiki/Correlation"') == 1

    def test_guide_has_no_controls_or_target_section(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="guide-controls"' not in html
        assert 'id="guide-target"' not in html
        assert "Using the report" not in html

    def test_guide_alerts_open_to_a_limit_and_possible_fixes(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index('id="guide-alerts"')
        section = html[
            start : html.index(
                "</section>",
                start,
            )
        ]
        assert section.count("<details") == 10
        assert section.count('class="alert-threshold"') == 10
        assert section.count(">Possible fix<") == 10
        assert section.count(">Sources<") == 10
        assert "feat.engineering" in section
        assert "log1p" in section
        assert "HasX" in section


class TestReproductionPage:
    @staticmethod
    def _snippet(html: str) -> str:
        from urllib.parse import unquote

        from shirabe_profiling.report.html import REPOSITORY_URL

        start = html.index(f'href="{REPOSITORY_URL}/issues/new?labels=bug')
        link = html[
            start : html.index(
                '"',
                start + 6,
            )
        ]
        return unquote(link)

    def test_has_its_own_tab_and_page(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="tab-page-feedback"' in html
        assert 'id="page-feedback"' in html

    def test_details_moved_off_the_report_page(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert html.index('id="reproduction-section"') > html.index('id="page-feedback"')

    def test_snippet_lists_only_changed_settings(self, mixed_df: pl.DataFrame):
        html = _render(
            mixed_df,
            ProfileConfig(
                title="Sales",
                missing_threshold=0.1,
            ),
        )
        snippet = self._snippet(html)
        assert "title='Sales'," in snippet
        assert "missing_threshold=0.1," in snippet
        assert "histogram_bins" not in snippet
        assert "report.to_html" in snippet

    def test_overview_mode_is_in_the_snippet(self, mixed_df: pl.DataFrame):
        html = _render(
            mixed_df,
            ProfileConfig(mode="overview"),
        )
        assert "mode='overview'," in self._snippet(html)

    def test_page_has_no_code_block_or_checklist(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="reproduction-code' not in html
        assert 'id="good-report-section"' not in html
        assert "What a good report includes" not in html
        assert "Reproduction code" not in html


class TestFeedbackTab:
    def test_third_tab_is_called_feedback(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'id="tab-page-feedback"' in html
        assert '<span class="tab-label">Feedback</span>' in html

    def test_tabs_keep_an_accessible_name_when_collapsed(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        assert 'aria-label="Guide"' in html
        assert 'aria-label="Feedback"' in html

    def test_issue_link_opens_a_prefilled_bug_report(self, mixed_df: pl.DataFrame):
        from urllib.parse import unquote

        from shirabe_profiling.report.html import REPOSITORY_URL

        html = _render(mixed_df)
        start = html.index(f'href="{REPOSITORY_URL}/issues/new?labels=bug')
        link = unquote(
            html[
                start : html.index(
                    '"',
                    start + 6,
                )
            ],
        )
        assert "labels=bug" in link
        assert "## Steps to Reproduce" in link
        assert "ProfileReport(" in link
        assert "- **polars version**:" in link

    def test_page_explains_what_to_include(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index('id="problem-section"')
        page = html[start : html.index('id="reproduction-section"')]
        assert "Open GitHub issue" in page

    def test_details_block_holds_counts_and_no_column_names(self):
        df = pl.DataFrame({"secret_column": [1, 2, None, 4], "other": [1, 2, 3, 4]})
        html = _render(df)
        start = html.index('id="reproduction-text">')
        block = html[
            start : html.index(
                "</pre>",
                start,
            )
        ]
        assert "rows: 4" in block
        assert "columns: 2" in block
        assert "column_types:" in block
        assert "secret_column" not in block

    def test_csv_download_sits_on_the_variables_section(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index('id="variables-section"')
        section = html[
            start : html.index(
                "</section>",
                start,
            )
        ]
        assert 'data-export="variables"' in section
        assert 'data-export="print"' not in html

    def test_source_is_an_icon_button(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        header = html[html.index('<header class="app-header"') : html.index("</header>")]
        assert 'aria-label="Source on GitHub"' in header

    def test_feature_request_comes_before_the_problem_report(self, mixed_df: pl.DataFrame):
        from urllib.parse import unquote

        from shirabe_profiling.report.html import REPOSITORY_URL

        html = _render(mixed_df)
        assert html.index('id="feature-section"') < html.index('id="problem-section"')
        assert html.index('id="problem-section"') < html.index('id="reproduction-section"')
        start = html.index(f'href="{REPOSITORY_URL}/issues/new?labels=enhancement')
        link = unquote(
            html[
                start : html.index(
                    '"',
                    start + 6,
                )
            ],
        )
        assert "## Proposed Solution" in link
        assert "## Alternatives Considered" in link
        assert "Open feature request" in html


class TestStrongestPairs:
    @staticmethod
    def _wide(columns: int) -> pl.DataFrame:
        rng = np.random.default_rng(4)
        base = rng.normal(size=200)
        data = {f"c{i}": rng.normal(size=200) for i in range(columns)}
        data["c0"] = base
        data["c1"] = base * 0.98 + rng.normal(size=200) * 0.05
        return pl.DataFrame(data)

    def test_wide_data_lists_the_strongest_pairs(self):
        html = _render(self._wide(8))
        assert 'class="pair-list"' in html
        start = html.index('class="pair-list"')
        first_row = html[
            start : html.index(
                "</li>",
                start,
            )
        ]
        assert "c0" in first_row
        assert "c1" in first_row

    def test_narrow_data_skips_the_list(self):
        html = _render(self._wide(4))
        assert 'class="pair-list"' not in html

    def test_pairs_are_limited_and_sorted(self):
        from shirabe_profiling.report.html import _strongest_pairs

        labels = ["a", "b", "c", "d"]
        data = [
            [1.0, 0.2, -0.9, 0.5],
            [0.2, 1.0, 0.1, float("nan")],
            [-0.9, 0.1, 1.0, 0.3],
            [0.5, float("nan"), 0.3, 1.0],
        ]

        pairs = _strongest_pairs(
            labels,
            data,
            limit=3,
        )

        assert [(p["a"], p["b"], p["value"]) for p in pairs] == [
            ("a", "c", -0.9),
            ("a", "d", 0.5),
            ("c", "d", 0.3),
        ]


class TestFeedbackPage:
    @staticmethod
    def _section(
        html: str,
        section_id: str,
    ) -> str:
        start = html.index(f'id="{section_id}"')
        return html[
            start : html.index(
                "</section>",
                start,
            )
        ]

    def test_the_tab_is_named_feedback_and_the_old_names_are_gone(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)

        assert 'aria-controls="page-feedback"' in html
        assert 'title="Feedback"' in html
        assert "page-help" not in html
        assert 'title="Help"' not in html
        assert ">Report a Problem<" not in html
        assert 'aria-label="Report a Problem"' not in html

    def test_the_tabs_run_report_guide_feedback(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)

        assert html.index('id="tab-page-report"') < html.index('id="tab-page-guide"')
        assert html.index('id="tab-page-guide"') < html.index('id="tab-page-feedback"')

    def test_the_sections_run_feature_problem_reproduction_about(
        self,
        mixed_df: pl.DataFrame,
    ):
        html = _render(mixed_df)
        page = html[html.index('id="page-feedback"') :]

        order = [
            page.index(f'id="{name}"')
            for name in (
                "feature-section",
                "problem-section",
                "reproduction-section",
                "about-section",
            )
        ]

        assert order == sorted(order)

    def test_the_copy_button_sits_in_the_reproduction_section(
        self,
        mixed_df: pl.DataFrame,
    ):
        html = _render(mixed_df)

        assert html.count('data-copy-target="reproduction-text"') == 1
        assert 'data-copy-target="reproduction-text"' in self._section(
            html,
            "reproduction-section",
        )
        assert "data-copy-target" not in self._section(
            html,
            "problem-section",
        )

    def test_the_copy_bar_comes_before_the_details(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        section = self._section(
            html,
            "reproduction-section",
        )

        assert section.index('class="code-bar"') < section.index('id="reproduction-text"')
        assert "Copy details" in section

    def test_the_steps_send_the_reader_to_the_reproduction_section(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        section = self._section(
            html,
            "problem-section",
        )

        assert "Choose Copy details in the Reproduction Details section below." in section
        assert "Open GitHub issue" in section
        assert section.index("Open GitHub issue") < section.index("Choose Copy details")

    def test_the_guide_points_to_the_feedback_tab_for_the_limits(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)

        assert "The Feedback tab lists the limits that this report used." in html
        assert "The Help tab" not in html


class TestAbout:
    @staticmethod
    def _section(
        html: str,
        section_id: str,
    ) -> str:
        start = html.index(f'id="{section_id}"')
        return html[
            start : html.index(
                "</section>",
                start,
            )
        ]

    def test_there_is_no_links_section(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)

        assert 'id="links-section"' not in html
        assert ">Links<" not in html

    def test_about_lists_the_package_version_and_time_without_a_license(
        self,
        mixed_df: pl.DataFrame,
    ):
        from shirabe_profiling.report.html import PACKAGE_NAME

        section = self._section(
            _render(mixed_df),
            "about-section",
        )

        assert f"<td>{PACKAGE_NAME}</td>" in section
        assert "<td>0.1.0</td>" in section
        assert ">License</td>" not in section
        assert re.search(
            r"Report created</td><td>\d{4}-\d{2}-\d{2} \d{2}:\d{2}</td>",
            section,
        )

    def test_about_has_no_credits_or_license_text(self, mixed_df: pl.DataFrame):
        section = self._section(
            _render(mixed_df),
            "about-section",
        )

        assert section.count("<table") == 1
        assert "open source projects" not in section
        for name in ("IBM Plex Sans", "Lilex", "Lucide", "Apache ECharts", "Tailwind CSS"):
            assert name not in section
        assert "icense" not in section


class TestLogo:
    def test_the_header_mark_is_an_inline_svg_that_follows_the_text_color(
        self,
        mixed_df: pl.DataFrame,
    ):
        html = _render(mixed_df)
        header = html[html.index('<header class="app-header"') : html.index("</header>")]

        assert '<span class="brand-mark" role="img" aria-label="shirabe">' in header
        assert 'fill="currentColor"' in header
        assert '<img class="brand-mark"' not in html

    def test_the_favicon_is_an_svg_tile(self, mixed_df: pl.DataFrame):
        import base64

        html = _render(mixed_df)
        match = re.search(
            r'<link rel="icon" type="image/svg\+xml" href="data:image/svg\+xml;base64,([^"]+)">',
            html,
        )

        assert match is not None
        favicon = base64.b64decode(match.group(1)).decode("utf-8")
        assert 'fill="#1a1a1a"' in favicon
        assert 'fill="#d4d4d4"' in favicon
        assert 'type="image/png"' not in html

    def test_the_old_png_logos_are_gone(self):
        from shirabe_profiling.report.html import _TEMPLATE_DIR

        assert not (_TEMPLATE_DIR / "icon.png").exists()
        assert not (_TEMPLATE_DIR / "dataxid_logo.png").exists()


class TestScrollContainment:
    def test_wide_areas_keep_only_the_sideways_swipe_inside_them(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index(".tab-list-header,")
        block = html[
            start : html.index(
                "}",
                start,
            )
        ]

        for selector in (
            ".view-tabs",
            ".chart-scroll",
            ".code-block",
            ".overflow-x-auto",
        ):
            assert selector in block
        assert "overscroll-behavior-x: contain;" in block
        assert "overscroll-behavior-y" not in block

    def test_a_vertical_scroll_over_a_wide_table_still_reaches_the_page(
        self,
        mixed_df: pl.DataFrame,
    ):
        html = _render(mixed_df)

        assert "overscroll-behavior: contain" not in html

    def test_only_a_list_that_overflows_keeps_its_vertical_scroll(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)
        start = html.index("[data-scrolls] {")
        block = html[
            start : html.index(
                "}",
                start,
            )
        ]

        assert "overscroll-behavior-y: contain;" in block
        assert "area.toggleAttribute('data-scrolls'" in html
        assert "area.scrollHeight - area.clientHeight > 1" in html

    def test_the_page_itself_keeps_the_default_scroll_chaining(self, mixed_df: pl.DataFrame):
        html = _render(mixed_df)

        assert "overscroll-behavior: none" not in html
        assert not re.search(
            r"(?m)^(html|body)\s*\{[^}]*overscroll-behavior",
            html,
        )
