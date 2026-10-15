from __future__ import annotations

import re

import numpy as np
import polars as pl

from shirabe_profiling import Alert, AlertType, ProfileConfig, ProfileReport
from shirabe_profiling.skew import MAX_COLUMNS, compute_skew_transforms


def _alert(
    column: str | None,
    alert_type: AlertType = AlertType.SKEWED,
    value: float = 5.0,
) -> Alert:
    return Alert(
        column=column,
        alert_type=alert_type,
        value=value,
    )


def _skewed(rows: int = 300) -> np.ndarray:
    return np.random.default_rng(0).exponential(size=rows) ** 2


def _compute(
    df: pl.DataFrame,
    alerts: list[Alert],
    config: ProfileConfig | None = None,
) -> list[dict]:
    return compute_skew_transforms(
        df,
        alerts,
        config or ProfileConfig(),
    )


class TestTransforms:
    def test_both_transforms_reduce_the_skew(self):
        df = pl.DataFrame({"x": _skewed()})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        original = abs(entry["original"]["skew_value"])
        assert entry["column"] == "x"
        assert abs(entry["log1p"]["skew_value"]) < original
        assert abs(entry["yeojohnson"]["skew_value"]) < original

    def test_a_transform_under_the_limit_is_marked_ok(self):
        df = pl.DataFrame({"x": _skewed()})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert entry["log1p"]["ok"] is True
        assert entry["yeojohnson"]["ok"] is True

    def test_every_transform_under_the_limit_is_marked_not_only_one(self):
        df = pl.DataFrame({"x": _skewed()})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        marked = [key for key in ("log1p", "yeojohnson") if entry[key]["ok"]]
        assert marked == ["log1p", "yeojohnson"]

    def test_a_column_that_stays_skewed_has_no_ok_mark(self):
        spikes = np.random.default_rng(0).exponential(size=20) * 500
        df = pl.DataFrame({"x": [0.0] * 280 + spikes.tolist()})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert entry["log1p"]["ok"] is False
        assert entry["yeojohnson"]["ok"] is False

    def test_the_limit_comes_from_the_config(self):
        df = pl.DataFrame({"x": _skewed()})

        entry = _compute(
            df,
            [_alert("x")],
            ProfileConfig(skewness_threshold=0.01),
        )[0]

        assert entry["log1p"]["ok"] is False
        assert entry["yeojohnson"]["ok"] is False

    def test_negative_values_leave_log1p_out(self):
        df = pl.DataFrame({"x": [-5.0, 0.0, 1.0, 2.0, 30.0, 400.0]})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert entry["log1p"] is None
        assert entry["yeojohnson"] is not None

    def test_the_fitted_power_is_reported(self):
        df = pl.DataFrame({"x": _skewed()})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert float(entry["yeojohnson"]["power"]) == float(entry["yeojohnson"]["power"])
        assert "power" not in entry["log1p"]

    def test_missing_values_stay_missing(self):
        values = _skewed().tolist()
        values[0] = None
        df = pl.DataFrame({"x": values})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert "numeric" not in entry["original"]
        assert entry["log1p"]["numeric"].count == 300
        assert entry["log1p"]["numeric"].missing_count == 1

    def test_a_long_column_still_fits_on_a_sample(self):
        df = pl.DataFrame({"x": _skewed(60_000)})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert entry["yeojohnson"]["numeric"].count == 60_000
        assert abs(entry["yeojohnson"]["skew_value"]) < abs(entry["original"]["skew_value"])


class TestNonZero:
    @staticmethod
    def _zero_heavy() -> pl.DataFrame:
        spikes = np.random.default_rng(0).exponential(size=40) * 100
        return pl.DataFrame({"x": [0.0] * 360 + spikes.tolist()})

    def test_a_zero_heavy_column_gets_a_non_zero_variant(self):
        entry = _compute(
            self._zero_heavy(),
            [_alert("x")],
        )[0]

        assert entry["nonzero"]["zeros"] == "90%"
        assert entry["nonzero"]["numeric"].count == 40
        assert entry["nonzero"]["numeric"].zeros_count == 0
        assert abs(entry["nonzero"]["skew_value"]) < abs(entry["original"]["skew_value"])

    def test_a_column_with_few_zeros_has_none(self):
        df = pl.DataFrame({"x": _skewed()})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert entry["nonzero"] is None

    def test_it_has_no_ok_mark(self):
        entry = _compute(
            self._zero_heavy(),
            [_alert("x")],
        )[0]

        assert "ok" not in entry["nonzero"]

    def test_the_zero_limit_comes_from_the_config(self):
        entry = _compute(
            self._zero_heavy(),
            [_alert("x")],
            ProfileConfig(zero_threshold=0.95),
        )[0]

        assert entry["nonzero"] is None

    def test_negative_values_below_minus_one_skip_it(self):
        df = pl.DataFrame({"x": [0.0] * 50 + [-5.0, 2.0, 30.0, 400.0]})

        entry = _compute(
            df,
            [_alert("x")],
        )[0]

        assert entry["nonzero"] is None


class TestSelection:
    def test_only_skewed_alerts_count(self):
        df = pl.DataFrame({"x": _skewed(), "y": _skewed()})

        result = _compute(
            df,
            [
                _alert("x"),
                _alert(
                    "y",
                    AlertType.HIGH_ZEROS,
                ),
            ],
        )

        assert [entry["column"] for entry in result] == ["x"]

    def test_text_and_constant_columns_are_skipped(self):
        df = pl.DataFrame({"t": ["a"] * 10, "c": [1.0] * 10})

        result = _compute(
            df,
            [_alert("t"), _alert("c")],
        )

        assert result == []

    def test_dataset_level_alerts_are_skipped(self):
        df = pl.DataFrame({"x": _skewed()})

        assert (
            _compute(
                df,
                [_alert(None)],
            )
            == []
        )

    def test_most_skewed_columns_come_first(self):
        df = pl.DataFrame({"a": _skewed(), "b": _skewed()})

        result = _compute(
            df,
            [
                _alert(
                    "a",
                    value=2.5,
                ),
                _alert(
                    "b",
                    value=9.0,
                ),
            ],
        )

        assert [entry["column"] for entry in result] == ["b", "a"]

    def test_the_list_is_capped(self):
        df = pl.DataFrame({f"c{i}": _skewed() for i in range(MAX_COLUMNS + 4)})

        result = _compute(
            df,
            [_alert(name) for name in df.columns],
        )

        assert len(result) == MAX_COLUMNS

    def test_overview_mode_returns_nothing(self):
        df = pl.DataFrame({"x": _skewed()})

        result = _compute(
            df,
            [_alert("x")],
            ProfileConfig(mode="overview"),
        )

        assert result == []


class TestColumnDetails:
    @staticmethod
    def _df() -> pl.DataFrame:
        return pl.DataFrame(
            {
                "income": _skewed(),
                "age": np.random.default_rng(1).normal(
                    40,
                    5,
                    300,
                ),
            },
        )

    @staticmethod
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

    def test_a_skewed_column_gets_view_tabs(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert 'class="tab-list view-tabs"' in panel
        assert 'id="tab-view-col_chart_0"' in panel
        assert 'data-chart-id="col_chart_0_log1p"' in panel
        assert 'data-chart-id="col_chart_0_yeojohnson"' in panel
        assert ">Distribution<" in panel

    def test_a_column_that_is_not_skewed_has_a_single_tab(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            1,
        )

        assert panel.count('role="tab"') == 1
        assert ">Distribution<" in panel
        assert "_log1p" not in panel

    def test_the_distribution_view_is_shown_first(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert 'id="pane-col_chart_0" aria-labelledby="tab-view-col_chart_0">' in panel
        assert (
            'id="pane-col_chart_0_log1p" aria-labelledby="tab-view-col_chart_0_log1p" hidden>'
            in panel
        )

    def test_each_view_has_its_own_chart_and_note(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert "reportTheme.mount('col_chart_0_log1p'" in panel
        assert "reportTheme.mount('col_chart_0_yeojohnson'" in panel
        assert "income after log1p" in panel
        assert "view-note" not in panel
        assert 'stat-label">Power<' in panel

    def test_a_transform_under_the_limit_is_marked_on_its_tab(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert 'title="Skew within the limit"' in panel
        assert "view-check" in panel

    def test_a_zero_heavy_column_gets_a_non_zero_tab(self):
        spikes = np.random.default_rng(0).exponential(size=40) * 100
        df = pl.DataFrame({"x": [0.0] * 360 + spikes.tolist()})

        html = ProfileReport(df).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert ">Non-zero<" in panel
        assert 'stat-label">Zeros set aside<' in panel

    def test_each_tab_has_its_own_stats_table(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert panel.count('<table class="table table-dense">') == 3

    def test_the_stats_table_follows_the_tab(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )
        original = panel[
            panel.index('id="pane-col_chart_0"') : panel.index('id="pane-col_chart_0_log1p"')
        ]
        logged = panel[
            panel.index('id="pane-col_chart_0_log1p"') : panel.index(
                'id="pane-col_chart_0_yeojohnson"',
            )
        ]

        def skewness(pane: str) -> float:
            match = re.search(
                r'Skewness</td><td class="num">(-?[\d.,]+)',
                pane,
            )
            assert match is not None
            return float(
                match.group(1).replace(
                    ",",
                    "",
                ),
            )

        assert skewness(original) > 2
        assert abs(skewness(logged)) < 2
        assert "<table" in original
        assert "<table" in logged

    def test_a_column_without_tabs_keeps_one_table(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            1,
        )

        assert panel.count('<table class="table table-dense">') == 1

    def test_the_tab_strip_sits_under_the_title_above_both_sides(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert panel.index('class="panel-heading"') < panel.index('class="tab-list view-tabs"')
        assert panel.index('class="tab-list view-tabs"') < panel.index(
            '<table class="table table-dense">',
        )

    def test_the_download_button_has_a_default_target(self):
        html = ProfileReport(self._df()).to_html()
        panel = self._panel(
            html,
            0,
        )

        assert 'data-save-png="col_chart_0"' in panel

    def test_overview_mode_has_no_transform_tabs(self):
        html = ProfileReport(
            self._df(),
            mode="overview",
        ).to_html()

        assert 'data-chart-id="col_chart_0_log1p"' not in html
        assert 'data-chart-id="col_chart_0"' in html

    def test_the_separate_section_is_gone(self):
        html = ProfileReport(self._df()).to_html()

        assert 'id="skew-section"' not in html
        assert "skew-data" not in html
        assert "Skewed Columns" not in html

    def test_the_guide_no_longer_has_a_panel(self):
        html = ProfileReport(self._df()).to_html()

        assert "Try it on your data" not in html
        assert 'class="fix-steps"' in html
