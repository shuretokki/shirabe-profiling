from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import numpy as np
import polars as pl

from shirabe_profiling import ProfileConfig, ProfileReport
from shirabe_profiling.analyzers.datetime import MAX_TIMELINE_BARS, analyze_datetime


def _panel(
    html: str,
    index: int,
) -> str:
    start = html.index(f'id="panel-col-{index}"')
    end = html.find(
        f'id="panel-col-{index + 1}"',
        start,
    )
    return html[
        start : end
        if end != -1
        else html.index(
            "</section>",
            start,
        )
    ]


def _skewed(rows: int = 300) -> np.ndarray:
    return np.random.default_rng(0).exponential(size=rows) ** 2


class TestAlertTags:
    def test_a_column_with_an_alert_shows_it_beside_the_type(self):
        df = pl.DataFrame({"income": _skewed()})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert 'title="Alert: Skewed"' in panel
        assert panel.index(">Numeric<") < panel.index(">Skewed<")

    def test_alert_tags_use_the_same_color_as_the_alerts_section(self):
        df = pl.DataFrame({"income": _skewed()})

        html = ProfileReport(df).to_html()
        panel = _panel(
            html,
            0,
        )

        assert '<span class="badge badge-warning" title="Alert: Skewed">' in panel

    def test_a_column_without_alerts_has_no_tags(self):
        df = pl.DataFrame(
            {
                "age": np.random.default_rng(1).integers(
                    20,
                    60,
                    300,
                ),
            },
        )

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert "badge-warning" not in panel

    def test_several_alerts_show_as_several_tags(self):
        values = [0.0] * 280 + (np.random.default_rng(0).exponential(size=20) * 500).tolist()
        df = pl.DataFrame({"x": values})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert ">Skewed<" in panel
        assert ">High Zeros<" in panel


class TestHighlightedRows:
    def test_the_skewness_row_is_marked_on_the_original(self):
        df = pl.DataFrame({"income": _skewed()})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )
        original = panel[
            panel.index('id="pane-col_chart_0"') : panel.index('id="pane-col_chart_0_log1p"')
        ]

        assert '<tr class="is-alert" title="Skewed"><td class="stat-label">Skewness' in original

    def test_a_transform_under_the_limit_is_not_marked(self):
        df = pl.DataFrame({"income": _skewed()})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )
        logged = panel[
            panel.index('id="pane-col_chart_0_log1p"') : panel.index(
                'id="pane-col_chart_0_yeojohnson"',
            )
        ]

        assert 'title="Skewed"' not in logged

    def test_a_transform_that_stays_skewed_keeps_the_mark(self):
        values = [0.0] * 280 + (np.random.default_rng(0).exponential(size=20) * 500).tolist()
        df = pl.DataFrame({"x": values})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )
        logged = panel[
            panel.index('id="pane-col_chart_0_log1p"') : panel.index(
                'id="pane-col_chart_0_yeojohnson"',
            )
        ]

        assert '<tr class="is-alert" title="Skewed"><td class="stat-label">Skewness' in logged

    def test_missing_zeros_and_imbalance_rows_are_marked(self):
        df = pl.DataFrame(
            {
                "gaps": [1.0] * 50 + [None] * 50,
                "zeros": [0.0] * 90 + [float(i) for i in range(10)],
                "flag": ["a"] * 98 + ["b", "c"],
            },
        )

        html = ProfileReport(df).to_html()

        assert (
            '<tr class="is-alert" title="High Missing"><td class="stat-label">Missing'
            in _panel(
                html,
                0,
            )
        )
        assert '<tr class="is-alert" title="High Zeros"><td class="stat-label">Zeros' in _panel(
            html,
            1,
        )
        assert (
            '<tr class="is-alert" title="Imbalanced"><td class="stat-label">Imbalance'
            in _panel(
                html,
                2,
            )
        )

    def test_the_note_under_the_chart_is_gone(self):
        df = pl.DataFrame({"income": _skewed()})

        html = ProfileReport(df).to_html()

        assert 'class="small muted view-note"' not in html

    def test_a_clean_column_has_no_marked_rows(self):
        df = pl.DataFrame(
            {
                "age": np.random.default_rng(1).integers(
                    20,
                    60,
                    300,
                ),
            },
        )

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert "is-alert" not in panel


class TestAlwaysATab:
    @staticmethod
    def _labels(panel: str) -> list[str]:
        strip = panel[
            panel.index('role="tablist"') : panel.index(
                "</div>",
                panel.index('role="tablist"'),
            )
        ]
        return re.findall(
            r'role="tab"[^>]*>([^<]+)',
            strip,
        )

    def test_every_column_type_gets_a_tab_named_for_its_chart(self):
        df = pl.DataFrame(
            {
                "num": [float(i % 37) for i in range(200)],
                "cat": ["a", "b", "c", "d"] * 50,
                "flag": [True, False] * 100,
                "when": [
                    datetime(
                        2024,
                        1,
                        1,
                    )
                    + timedelta(days=i)
                    for i in range(200)
                ],
            },
        )

        html = ProfileReport(df).to_html()

        assert self._labels(
            _panel(
                html,
                0,
            ),
        ) == ["Distribution"]
        assert self._labels(
            _panel(
                html,
                1,
            ),
        ) == ["Top Values"]
        assert self._labels(
            _panel(
                html,
                2,
            ),
        ) == ["Distribution"]
        assert self._labels(
            _panel(
                html,
                3,
            ),
        ) == ["Timeline"]

    def test_a_single_tab_is_selected_and_shows_its_pane(self):
        df = pl.DataFrame({"cat": ["a", "b", "c", "d"] * 50})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert 'aria-selected="true"' in panel
        assert 'id="pane-col_chart_0"' in panel
        assert "hidden>" not in panel[panel.index('id="pane-col_chart_0"') :][:120]

    def test_a_column_without_a_chart_still_has_a_tab(self):
        df = pl.DataFrame(
            {
                "a": pl.Series(
                    [None] * 10,
                    dtype=pl.Datetime,
                ),
                "b": list(range(10)),
            },
        )

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert self._labels(panel) == ["Timeline"]
        assert "No chart available" in panel

    def test_skewed_columns_keep_the_distribution_tab_first(self):
        df = pl.DataFrame({"income": _skewed()})

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert self._labels(panel)[:2] == ["Distribution", "log1p"]


class TestMarksSurviveATabChange:
    @staticmethod
    def _df() -> pl.DataFrame:
        values = [0.0] * 60 + _skewed(200).tolist() + [None] * 40
        return pl.DataFrame({"x": values})

    @staticmethod
    def _pane(
        html: str,
        suffix: str = "",
    ) -> str:
        panel = _panel(
            html,
            0,
        )
        start = panel.index(f'id="pane-col_chart_0{suffix}"')
        end = panel.find(
            'id="pane-',
            start + 10,
        )
        return panel[start : end if end != -1 else len(panel)]

    def test_the_original_shows_every_mark(self):
        pane = self._pane(ProfileReport(self._df()).to_html())

        assert 'title="High Missing"' in pane
        assert 'title="High Zeros"' in pane
        assert 'title="Skewed"' in pane

    def test_an_unchanged_row_keeps_its_mark_on_a_transform_tab(self):
        pane = self._pane(
            ProfileReport(self._df()).to_html(),
            "_log1p",
        )

        assert 'title="High Missing"' in pane
        assert 'title="High Zeros"' in pane

    def test_a_row_that_changes_loses_its_mark(self):
        pane = self._pane(
            ProfileReport(self._df()).to_html(),
            "_nonzero",
        )

        assert 'title="High Missing"' not in pane
        assert 'title="High Zeros"' not in pane

    def test_the_skewness_mark_follows_the_new_value(self):
        html = ProfileReport(self._df()).to_html()

        assert 'title="Skewed"' in self._pane(html)
        assert 'title="Skewed"' not in self._pane(
            html,
            "_yeojohnson",
        )


class TestFillLayout:
    def test_panels_and_split_carry_the_fill_classes(self):
        df = pl.DataFrame(
            {
                "income": _skewed(),
                "age": np.random.default_rng(1).integers(
                    20,
                    60,
                    300,
                ),
            },
        )

        html = ProfileReport(df).to_html()

        assert 'class="col-panel" id="panel-col-0"' in html
        assert 'class="col-pane" id="pane-col_chart_0"' in html
        assert "grid grid-cols-1 lg:grid-cols-2 col-split" in _panel(
            html,
            1,
        )

    def test_the_fill_rules_apply_only_from_the_desktop_width(self):
        df = pl.DataFrame(
            {
                "age": np.random.default_rng(1).integers(
                    20,
                    60,
                    300,
                ),
            },
        )

        html = ProfileReport(df).to_html()
        start = html.index('[data-layout="list"] .columns-detail {\n    display: flex;')

        assert (
            html.rfind(
                "@media (min-width: 48rem) {",
                0,
                start,
            )
            > html.rfind(
                "}\n\n",
                0,
                start,
            )
            - 400
        )
        assert '[data-layout="list"] .col-split {' in html


class TestDatetimeTimeline:
    @staticmethod
    def _stats(values: list):
        return analyze_datetime(
            pl.DataFrame({"t": values}),
            "t",
            ProfileConfig(),
        )

    def test_a_short_span_counts_per_day(self):
        stats = self._stats(
            [
                date(
                    2024,
                    1,
                    1,
                )
                + timedelta(days=i % 40)
                for i in range(500)
            ],
        )

        assert stats.timeline_unit == "day"
        assert len(stats.timeline) == 40
        assert stats.timeline[0]["label"] == "2024-01-01"

    def test_a_few_years_count_per_month(self):
        stats = self._stats(
            [
                datetime(
                    2021,
                    1,
                    1,
                )
                + timedelta(days=i % 1000)
                for i in range(2000)
            ],
        )

        assert stats.timeline_unit == "month"
        assert stats.timeline[0]["label"] == "2021-01"

    def test_a_long_span_counts_per_year(self):
        stats = self._stats(
            [
                datetime(
                    2000 + i % 21,
                    3,
                    1,
                )
                for i in range(400)
            ],
        )

        assert stats.timeline_unit == "year"
        assert len(stats.timeline) == 21

    def test_a_span_of_hours_counts_per_hour(self):
        stats = self._stats(
            [
                datetime(
                    2024,
                    5,
                    1,
                )
                + timedelta(hours=i % 40)
                for i in range(300)
            ],
        )

        assert stats.timeline_unit == "hour"
        assert stats.timeline[0]["label"] == "2024-05-01 00:00"

    def test_the_number_of_bars_stays_under_the_limit(self):
        stats = self._stats(
            [
                datetime(
                    1900,
                    1,
                    1,
                )
                + timedelta(days=37 * i)
                for i in range(3000)
            ],
        )

        assert len(stats.timeline) <= MAX_TIMELINE_BARS or stats.timeline_unit == "year"

    def test_empty_periods_show_as_zero(self):
        stats = self._stats(
            [
                datetime(
                    2024,
                    1,
                    5,
                ),
                datetime(
                    2024,
                    4,
                    9,
                ),
                datetime(
                    2024,
                    4,
                    20,
                ),
            ],
        )

        assert [(bar["label"], bar["count"]) for bar in stats.timeline] == [
            ("2024-01", 1),
            ("2024-02", 0),
            ("2024-03", 0),
            ("2024-04", 2),
        ]

    def test_every_non_missing_row_is_counted_once(self):
        stats = self._stats(
            [
                datetime(
                    2024,
                    1,
                    5,
                ),
                None,
                datetime(
                    2024,
                    3,
                    9,
                ),
                None,
            ],
        )

        assert sum(bar["count"] for bar in stats.timeline) == 2

    def test_a_single_value_gets_one_daily_bar(self):
        stats = self._stats(
            [
                datetime(
                    2024,
                    1,
                    1,
                ),
            ]
            * 5,
        )

        assert stats.timeline_unit == "day"
        assert stats.timeline == [{"label": "2024-01-01", "count": 5}]

    def test_an_all_missing_column_has_no_timeline(self):
        stats = analyze_datetime(
            pl.DataFrame(
                {
                    "t": pl.Series(
                        [None, None],
                        dtype=pl.Datetime,
                    ),
                },
            ),
            "t",
            ProfileConfig(),
        )

        assert stats.timeline == []
        assert stats.timeline_unit == ""

    def test_the_report_draws_a_chart_for_a_datetime_column(self):
        df = pl.DataFrame(
            {
                "sold": [
                    datetime(
                        2021,
                        1,
                        1,
                    )
                    + timedelta(days=i % 500)
                    for i in range(1000)
                ],
            },
        )

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert "reportTheme.mount('col_chart_0'" in panel
        assert "sold by month" in panel
        assert "No chart available" not in panel

    def test_an_all_missing_datetime_column_still_says_no_chart(self):
        df = pl.DataFrame(
            {
                "a": pl.Series(
                    [None] * 10,
                    dtype=pl.Datetime,
                ),
                "b": list(range(10)),
            },
        )

        panel = _panel(
            ProfileReport(df).to_html(),
            0,
        )

        assert "No chart available" in panel


class TestCorrelationTags:
    @staticmethod
    def _df() -> pl.DataFrame:
        base = np.random.default_rng(3).normal(size=200)
        noise = np.random.default_rng(4).normal(
            scale=0.01,
            size=200,
        )
        return pl.DataFrame(
            {
                "a": base,
                "b": base * 2 + noise,
                "c": base * 3 - noise,
                "other": np.random.default_rng(5).normal(size=200),
            },
        )

    @staticmethod
    def _heading(
        html: str,
        index: int,
    ) -> str:
        panel = _panel(
            html,
            index,
        )
        start = panel.index('class="panel-heading"')
        return panel[
            start : panel.index(
                "</div>",
                start,
            )
        ]

    def test_a_column_in_several_pairs_gets_one_tag(self):
        html = ProfileReport(self._df()).to_html()

        assert (
            self._heading(
                html,
                0,
            ).count(">High Correlation<")
            == 1
        )

    def test_the_title_lists_the_partner_columns(self):
        html = ProfileReport(self._df()).to_html()

        assert 'title="Alert: High Correlation with b, c"' in self._heading(
            html,
            0,
        )
        assert 'title="Alert: High Correlation with a, c"' in self._heading(
            html,
            1,
        )

    def test_the_partner_column_is_tagged_too(self):
        html = ProfileReport(self._df()).to_html()

        assert 'title="Alert: High Correlation with a, b"' in self._heading(
            html,
            2,
        )

    def test_an_unrelated_column_has_no_correlation_tag(self):
        html = ProfileReport(self._df()).to_html()

        assert "High Correlation" not in self._heading(
            html,
            3,
        )

    def test_other_alert_types_are_not_merged_by_mistake(self):
        values = [0.0] * 60 + _skewed(200).tolist() + [None] * 40
        df = pl.DataFrame({"x": values})

        heading = self._heading(
            ProfileReport(df).to_html(),
            0,
        )

        assert heading.count(">Skewed<") == 1
        assert heading.count(">High Zeros<") == 1
        assert heading.count(">High Missing<") == 1


class TestSidebarHeight:
    def test_the_sidebar_is_sized_by_the_panel_not_capped(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()
        start = html.index('[data-layout="list"] .columns-nav {')
        rule = html[
            start : html.index(
                "}",
                start,
            )
        ]

        assert "min-height: 40rem" in rule
        assert "max-height" not in rule

    def test_the_list_scrolls_inside_the_sidebar_without_sizing_it(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()
        start = html.index('[data-layout="list"] .chip-list {')
        rule = html[
            start : html.index(
                "}",
                start,
            )
        ]

        assert "flex: 1 1 0" in rule
        assert "min-height: 0" in rule
        assert "overflow-y: auto" in rule

    def test_a_phone_gets_a_fixed_height_sidebar(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()
        start = html.index('@media (max-width: 47.99rem) {\n  [data-layout="list"] .columns {')
        block = html[
            start : html.index(
                "\n}\n",
                start,
            )
        ]

        assert "height: 14rem" in block

    def test_the_highlight_is_on_the_row_not_on_each_cell(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()

        assert ".table tr.is-alert {\n  background: var(--warning-bg);" in html
        assert ".table tr.is-alert td {" not in html


def _css_block(
    html: str,
    opening: str,
) -> str:
    start = html.index(opening)
    depth = 0
    for position in range(
        html.index(
            "{",
            start,
        ),
        len(html),
    ):
        if html[position] == "{":
            depth += 1
        elif html[position] == "}":
            depth -= 1
            if depth == 0:
                return html[start : position + 1]
    return html[start:]


class TestHeaderGap:
    def test_the_page_tab_grows_with_the_icon_buttons(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()
        rule = _css_block(
            html,
            ".page-bar .tab {",
        )

        assert "min-height: max(2rem, calc(var(--h-default) + 0.5rem))" in rule

    def test_the_desktop_height_is_unchanged(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()

        assert "--h-default: 1.375rem" in html
        assert "max(2rem, calc(1.375rem + 0.5rem))" not in html


class TestNarrowTabs:
    @staticmethod
    def _block() -> str:
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})
        html = ProfileReport(df).to_html()
        return _css_block(
            html,
            "@media (max-width: 25.75rem) {",
        )

    def test_the_breakpoint_reaches_a_412_pixel_phone(self):
        assert 25.75 * 16 == 412

    def test_the_sample_and_correlation_tabs_scroll_sideways(self):
        block = self._block()

        assert ".tab-bar .tab-list,\n  #corr-tabs {" in block
        assert "overflow-x: auto" in block

    def test_tabs_keep_their_width_instead_of_squeezing(self):
        block = self._block()

        assert "flex: none" in block
        assert "white-space: nowrap" in block

    def test_the_sample_tools_move_to_their_own_row(self):
        block = self._block()

        assert ".tab-bar {\n    flex-wrap: wrap;" in block
        assert ".tab-bar .tab-bar-tools {\n    flex: 1 1 100%;" in block
        assert "justify-content: flex-end" in block

    def test_the_rules_come_after_the_base_tab_rules(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()

        assert html.index("@media (max-width: 25.75rem) {") > html.index(
            ".tab-bar .tab-bar-tools {",
        )


class TestEqualDetailHeight:
    def test_the_panel_height_follows_the_tallest_table(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()
        rule = _css_block(
            html,
            '[data-layout="list"] .columns-detail {',
        )

        assert "var(--detail-rows, 0) * var(--h-list-row)" in rule
        assert "var(--h-medium)" in rule

    def test_the_page_script_counts_the_rows_of_every_table(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()

        assert "querySelectorAll('table.table-dense')" in html
        assert "setProperty('--detail-rows'" in html

    def test_a_column_with_extra_rows_is_the_tallest_case(self):
        values = [0.0] * 60 + _skewed(200).tolist()
        df = pl.DataFrame({"x": values, "y": [float(i % 37) for i in range(260)]})

        html = ProfileReport(df).to_html()
        panel = _panel(
            html,
            0,
        )
        yeo = panel[
            panel.index('id="pane-col_chart_0_yeojohnson"') : panel.index(
                'id="pane-col_chart_0_nonzero"',
            )
        ]
        plain = _panel(
            html,
            1,
        )

        assert yeo.count("<tr") > plain.count("<tr")
        assert 'stat-label">Power<' in yeo

    def test_the_rule_applies_only_from_the_desktop_width(self):
        df = pl.DataFrame({"x": [float(i % 37) for i in range(200)]})

        html = ProfileReport(df).to_html()
        block = _css_block(
            html,
            '@media (min-width: 48rem) {\n  [data-layout="list"] .columns-detail {',
        )

        assert "--detail-rows" in block
