# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from shirabe_profiling import AlertType, ProfileConfig, ProfileReport
from shirabe_profiling.target import compute_target, target_alerts
from shirabe_profiling.type_inference import infer_types


def _survival() -> pl.DataFrame:
    """Women survive in 90 of 100 rows and men in 20 of 100 rows."""
    return pl.DataFrame(
        {
            "survived": [1] * 90 + [0] * 10 + [0] * 80 + [1] * 20,
            "sex": ["f"] * 100 + ["m"] * 100,
            "noise": [i % 7 for i in range(200)],
        },
    )


def _analyze(
    df: pl.DataFrame,
    **options,
):
    config = ProfileConfig(**options)
    return compute_target(
        df,
        infer_types(
            df,
            config,
        ),
        config,
    ), config


class TestTask:
    def test_whole_number_target_with_few_values_is_classification(self):
        analysis, _ = _analyze(
            _survival(),
            target="survived",
        )

        assert analysis.summary.task == "classification"

    def test_continuous_target_is_regression(self):
        rng = np.random.default_rng(1)
        df = pl.DataFrame(
            {
                "price": rng.normal(
                    100,
                    10,
                    200,
                ),
                "x": rng.normal(size=200),
            },
        )

        analysis, _ = _analyze(
            df,
            target="price",
        )

        assert analysis.summary.task == "regression"

    def test_text_target_is_refused(self):
        df = pl.DataFrame(
            {"note": [f"a long unique note number {i}" for i in range(50)], "x": range(50)},
        )

        with pytest.raises(
            ValueError,
            match="TEXT",
        ):
            _analyze(
                df,
                target="note",
            )

    def test_unknown_target_names_the_columns(self):
        with pytest.raises(
            ValueError,
            match="'nope'.*survived",
        ):
            _analyze(
                _survival(),
                target="nope",
            )

    def test_no_target_means_no_analysis(self):
        analysis, _ = _analyze(_survival())

        assert analysis is None


class TestClassification:
    def test_summary_counts_the_classes(self):
        summary = _analyze(
            _survival(),
            target="survived",
        )[0].summary

        assert summary.rows == 200
        assert summary.missing == 0
        assert [(c.label, c.count) for c in summary.classes] == [("1", 110), ("0", 90)]
        assert summary.focus == "1"
        assert summary.overall == pytest.approx(0.55)
        assert summary.value_label == "Share with survived = 1"

    def test_rows_without_a_target_are_set_aside(self):
        df = _survival().with_columns(
            pl.when(pl.int_range(pl.len()) < 10)
            .then(None)
            .otherwise(pl.col("survived"))
            .alias("survived"),
        )

        summary = _analyze(
            df,
            target="survived",
        )[0].summary

        assert summary.rows == 190
        assert summary.missing == 10

    def test_breakdown_gives_the_rate_for_each_level(self):
        analysis, _ = _analyze(
            _survival(),
            target="survived",
        )

        sex = next(item for item in analysis.breakdowns if item.column == "sex")
        rates = {b.label: (b.count, b.value) for b in sex.bins}
        assert rates == {"f": (100, pytest.approx(0.9)), "m": (100, pytest.approx(0.2))}

    def test_strong_column_ranks_above_noise(self):
        analysis, _ = _analyze(
            _survival(),
            target="survived",
        )

        assert [link.column for link in analysis.links] == ["sex", "noise"]
        assert analysis.links[0].association > 0.5
        assert analysis.links[1].association < 0.2

    @pytest.mark.parametrize(
        ("labels", "expected"),
        [
            (["yes"] * 30 + ["no"] * 70, "yes"),
            (["yes"] * 70 + ["no"] * 30, "yes"),
            (["a"] * 70 + ["b"] * 30, "b"),
            (["a"] * 50 + ["b"] * 30 + ["c"] * 20, "a"),
        ],
    )
    def test_followed_class(
        self,
        labels,
        expected,
    ):
        df = pl.DataFrame({"label": labels, "x": list(range(len(labels)))})

        assert (
            _analyze(
                df,
                target="label",
            )[0].summary.focus
            == expected
        )

    def test_numeric_column_is_cut_into_bins_with_counts(self):
        rng = np.random.default_rng(2)
        age = rng.uniform(
            0,
            80,
            400,
        )
        df = pl.DataFrame({"y": (age > 40).astype(int), "age": age})

        analysis, _ = _analyze(
            df,
            target="y",
        )

        bins = analysis.breakdowns[0].bins
        assert sum(b.count for b in bins) == 400
        assert bins[0].value == 0.0
        assert bins[-1].value == 1.0
        assert analysis.links[0].direction > 0.8

    def test_few_whole_values_are_listed_one_by_one(self):
        df = _survival().with_columns((pl.col("survived") + pl.col("noise") % 3).alias("level"))

        analysis, _ = _analyze(
            df,
            target="survived",
        )

        level = next(item for item in analysis.breakdowns if item.column == "level")
        assert [b.label for b in level.bins] == ["0", "1", "2", "3"]

    def test_many_levels_are_set_aside(self):
        rng = np.random.default_rng(3)
        df = pl.DataFrame(
            {
                "y": rng.integers(
                    0,
                    2,
                    300,
                ),
                "code": [f"c{i % 60}" for i in range(300)],
                "x": rng.normal(size=300),
            },
        )

        analysis, _ = _analyze(
            df,
            target="y",
        )

        assert analysis.skipped == ["code"]
        assert "code" not in [link.column for link in analysis.links]

    def test_extra_levels_are_merged_into_other(self):
        rng = np.random.default_rng(4)
        df = pl.DataFrame(
            {
                "y": rng.integers(
                    0,
                    2,
                    600,
                ),
                "c": [f"c{i % 20}" for i in range(600)],
            },
        )

        analysis, _ = _analyze(
            df.with_columns(pl.col("y")),
            target="y",
            target_max_features=3,
        )

        bins = next(item for item in analysis.breakdowns if item.column == "c").bins
        assert len(bins) == 12
        assert bins[-1].label == "Other"
        assert sum(b.count for b in bins) == 600


class TestRegression:
    def _frame(self) -> pl.DataFrame:
        rng = np.random.default_rng(5)
        area = rng.uniform(
            30,
            300,
            500,
        )
        price = np.exp(
            10
            + area / 100
            + rng.normal(
                0,
                0.1,
                500,
            ),
        )
        return pl.DataFrame(
            {
                "price": price,
                "area": area,
                "junk": rng.normal(size=500),
            },
        )

    def test_summary_has_the_usual_numbers(self):
        summary = _analyze(
            self._frame(),
            target="price",
        )[0].summary

        assert set(summary.stats) == {"mean", "median", "std", "min", "max", "skew"}
        assert summary.overall == pytest.approx(summary.stats["mean"])
        assert summary.value_label == "Mean of price"

    def test_log_transform_lowers_the_skew(self):
        summary = _analyze(
            self._frame(),
            target="price",
        )[0].summary

        assert summary.stats["skew"] > 1
        assert abs(summary.log_skew) < abs(summary.stats["skew"])

    def test_negative_values_have_no_log_skew(self):
        df = pl.DataFrame(
            {
                "y": np.linspace(
                    -5,
                    5,
                    100,
                ),
                "x": np.linspace(
                    0,
                    1,
                    100,
                ),
            },
        )

        assert (
            _analyze(
                df,
                target="y",
            )[0].summary.log_skew
            is None
        )

    def test_direction_follows_the_sign_of_the_link(self):
        analysis, _ = _analyze(
            self._frame(),
            target="price",
        )
        links = {link.column: link for link in analysis.links}

        assert links["area"].direction > 0.9
        assert links["area"].association > links["junk"].association

    def test_breakdown_value_is_the_mean_of_the_target(self):
        analysis, _ = _analyze(
            self._frame(),
            target="price",
        )

        bins = next(item for item in analysis.breakdowns if item.column == "area").bins
        assert bins[0].value < bins[-1].value


class TestMissingValues:
    def test_gap_between_missing_and_present_rows(self):
        df = _survival().with_columns(
            pl.when(pl.col("survived") == 0).then(None).otherwise(pl.col("noise")).alias("cabin"),
        )

        analysis, _ = _analyze(
            df,
            target="survived",
        )

        link = analysis.missing_links[0]
        assert link.column == "cabin"
        assert link.missing_rows == 90
        assert link.missing_value == 0.0
        assert link.present_value == 1.0
        assert link.gap == -1.0

    def test_small_groups_are_ignored(self):
        df = _survival().with_columns(
            pl.when(pl.int_range(pl.len()) < 3)
            .then(None)
            .otherwise(pl.col("noise"))
            .alias("rare"),
        )

        assert (
            _analyze(
                df,
                target="survived",
            )[0].missing_links
            == []
        )


class TestLeakage:
    def test_close_copy_of_the_target_raises_an_alert(self):
        df = _survival().with_columns((pl.col("survived") * 10).alias("answer"))

        analysis, config = _analyze(
            df,
            target="survived",
        )
        alerts = target_alerts(
            analysis,
            config,
        )

        assert [a.column for a in alerts] == ["answer"]
        assert alerts[0].alert_type is AlertType.TARGET_LEAKAGE
        assert alerts[0].details == {"target": "survived"}

    def test_normal_columns_raise_none(self):
        analysis, config = _analyze(
            _survival(),
            target="survived",
        )

        assert (
            target_alerts(
                analysis,
                config,
            )
            == []
        )

    def test_threshold_is_configurable(self):
        analysis, config = _analyze(
            _survival(),
            target="survived",
            leakage_threshold=0.5,
        )

        assert [
            a.column
            for a in target_alerts(
                analysis,
                config,
            )
        ] == ["sex"]


class TestProfileReport:
    def test_target_property_and_alert_list(self):
        df = _survival().with_columns((pl.col("survived") * 10).alias("answer"))

        report = ProfileReport(
            df,
            target="survived",
        )

        assert report.target.summary.column == "survived"
        assert any(a.alert_type is AlertType.TARGET_LEAKAGE for a in report.alerts)

    def test_no_target_no_section(self):
        report = ProfileReport(_survival())

        assert report.target is None
        assert 'id="target-section"' not in report.to_html()

    def test_html_has_every_part(self):
        df = _survival().with_columns(
            pl.when(pl.col("survived") == 0).then(None).otherwise(pl.col("noise")).alias("cabin"),
        )

        html = ProfileReport(
            df,
            target="survived",
        ).to_html()

        assert 'id="target-section"' in html
        assert "Link to target" in html
        assert "How the target changes" in html
        assert "Missing values and the target" in html
        assert "target_chart_0" in html

    def test_parts_are_tabs_and_the_first_one_shows(self):
        df = _survival().with_columns(
            pl.when(pl.col("survived") == 0).then(None).otherwise(pl.col("noise")).alias("cabin"),
        )

        html = ProfileReport(
            df,
            target="survived",
        ).to_html()

        assert 'id="target-tabs"' in html
        assert (
            'id="tab-target-links" aria-controls="panel-target-links" aria-selected="true"' in html
        )
        assert (
            'id="tab-target-charts" aria-controls="panel-target-charts" aria-selected="false"'
            in html
        )
        assert 'id="panel-target-links" aria-labelledby="tab-target-links">' in html
        assert 'id="panel-target-charts" aria-labelledby="tab-target-charts" hidden>' in html
        assert 'id="panel-target-missing" aria-labelledby="tab-target-missing" hidden>' in html

    def test_tabs_have_icons_and_labels(self):
        html = ProfileReport(
            _survival(),
            target="survived",
        ).to_html()

        assert 'class="tab-label">Link to target</span>' in html
        assert 'class="tab-label">How the target changes</span>' in html

    def test_a_missing_part_leaves_no_empty_tab(self):
        html = ProfileReport(
            _survival(),
            target="survived",
        ).to_html()

        assert 'id="tab-target-missing"' not in html
        assert 'id="tab-target-links"' in html

    def test_regression_html_mentions_the_log_transform(self):
        rng = np.random.default_rng(6)
        area = rng.uniform(
            30,
            300,
            300,
        )
        df = pl.DataFrame({"price": np.exp(10 + area / 60), "area": area})

        html = ProfileReport(
            df,
            target="price",
        ).to_html()

        assert "Log transform" in html
        assert "Mean of price" in html

    def test_reproduction_code_and_details_name_the_target(self):
        report = ProfileReport(
            _survival(),
            target="survived",
        )

        assert "target='survived'," in report._call_code
        assert report.overview["reproduction"]["target.column"] == "survived"

    def test_to_dict_carries_the_target(self):
        data = ProfileReport(
            _survival(),
            target="survived",
        ).to_dict()

        assert data["target"]["summary"]["task"] == "classification"

    def test_guide_lists_the_alert(self):
        assert "Target Leakage" in ProfileReport(_survival()).to_html()


class TestConfig:
    @pytest.mark.parametrize(
        "options",
        [
            {"target": ""},
            {"target_max_features": 0},
            {"leakage_threshold": 0.0},
            {"leakage_threshold": 1.5},
        ],
    )
    def test_bad_values_are_refused(self, options):
        with pytest.raises(ValueError):
            ProfileConfig(**options)
