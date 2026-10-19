# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import polars as pl
import pytest

from shirabe_profiling import ProfileReport
from shirabe_profiling.alerts import Alert, AlertType, alert_order, check_quality
from shirabe_profiling.analyzers import analyze
from shirabe_profiling.config import ProfileConfig
from shirabe_profiling.correlations import compute_correlations
from shirabe_profiling.dataset_overview import compute_overview
from shirabe_profiling.datasets import make_homes
from shirabe_profiling.type_inference import infer_types


def _get_alerts(
    df: pl.DataFrame,
    config: ProfileConfig | None = None,
) -> list[Alert]:
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
    correlations = compute_correlations(
        df,
        column_types,
        config,
    )
    return check_quality(
        column_stats,
        overview,
        config,
        correlations,
    )


def _alert_types(alerts: list[Alert]) -> set[AlertType]:
    return {a.alert_type for a in alerts}


def _alerts_for_column(
    alerts: list[Alert],
    col: str,
) -> list[Alert]:
    return [a for a in alerts if a.column == col]


class TestHighMissing:
    def test_triggers_above_threshold(self):
        df = pl.DataFrame({"a": [1, None, None, None, None]})
        alerts = _get_alerts(
            df,
            ProfileConfig(missing_threshold=0.05),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.HIGH_MISSING for a in col_alerts)

    def test_no_alert_below_threshold(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, None]})
        alerts = _get_alerts(
            df,
            ProfileConfig(missing_threshold=0.5),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert not any(a.alert_type == AlertType.HIGH_MISSING for a in col_alerts)

    def test_missing_value_correct(self):
        df = pl.DataFrame({"a": [1, None, None, 4, 5]})
        alerts = _get_alerts(
            df,
            ProfileConfig(missing_threshold=0.05),
        )
        missing_alerts = [
            a for a in alerts if a.alert_type == AlertType.HIGH_MISSING and a.column == "a"
        ]
        assert len(missing_alerts) == 1
        assert missing_alerts[0].value == pytest.approx(0.4)


class TestConstant:
    def test_single_value_triggers(self):
        df = pl.DataFrame({"a": [42, 42, 42, 42, 42]})
        alerts = _get_alerts(df)
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.CONSTANT for a in col_alerts)

    def test_multiple_values_no_alert(self):
        df = pl.DataFrame({"a": [1, 2, 3]})
        alerts = _get_alerts(df)
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert not any(a.alert_type == AlertType.CONSTANT for a in col_alerts)


class TestHighCardinality:
    def test_numeric_high_cardinality(self):
        df = pl.DataFrame({"a": list(range(100))})
        alerts = _get_alerts(
            df,
            ProfileConfig(cardinality_threshold=0.95),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.HIGH_CARDINALITY for a in col_alerts)

    def test_categorical_high_cardinality(self):
        df = pl.DataFrame({"a": [f"val_{i}" for i in range(20)]})
        alerts = _get_alerts(
            df,
            ProfileConfig(
                cardinality_threshold=0.95,
                text_unique_ratio=1.0,
            ),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.HIGH_CARDINALITY for a in col_alerts)


class TestDuplicates:
    def test_duplicates_trigger(self):
        df = pl.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        alerts = _get_alerts(df)
        assert any(a.alert_type == AlertType.DUPLICATES for a in alerts)

    def test_no_duplicates(self):
        df = pl.DataFrame({"a": [1, 2, 3]})
        alerts = _get_alerts(df)
        assert not any(a.alert_type == AlertType.DUPLICATES for a in alerts)

    def test_duplicate_is_dataset_level(self):
        df = pl.DataFrame({"a": [1, 1, 2]})
        dup_alerts = [a for a in _get_alerts(df) if a.alert_type == AlertType.DUPLICATES]
        assert all(a.column is None for a in dup_alerts)


class TestHighZeros:
    def test_zeros_trigger(self):
        df = pl.DataFrame({"a": [0, 0, 0, 1, 2]})
        alerts = _get_alerts(
            df,
            ProfileConfig(zero_threshold=0.05),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.HIGH_ZEROS for a in col_alerts)

    def test_no_zeros_no_alert(self):
        df = pl.DataFrame({"a": [1, 2, 3]})
        alerts = _get_alerts(df)
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert not any(a.alert_type == AlertType.HIGH_ZEROS for a in col_alerts)


class TestSkewed:
    def test_skewed_triggers(self):
        # highly right-skewed distribution
        df = pl.DataFrame({"a": [1] * 90 + [1000] * 10})
        alerts = _get_alerts(
            df,
            ProfileConfig(skewness_threshold=2.0),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.SKEWED for a in col_alerts)

    def test_symmetric_no_alert(self):
        df = pl.DataFrame({"a": list(range(1, 101))})
        alerts = _get_alerts(
            df,
            ProfileConfig(skewness_threshold=2.0),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert not any(a.alert_type == AlertType.SKEWED for a in col_alerts)


class TestImbalanced:
    def test_boolean_imbalanced(self):
        df = pl.DataFrame({"a": [True] * 95 + [False] * 5})
        alerts = _get_alerts(
            df,
            ProfileConfig(imbalance_threshold=0.9),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.IMBALANCED for a in col_alerts)

    def test_boolean_balanced_no_alert(self):
        df = pl.DataFrame({"a": [True, False, True, False]})
        alerts = _get_alerts(
            df,
            ProfileConfig(imbalance_threshold=0.9),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert not any(a.alert_type == AlertType.IMBALANCED for a in col_alerts)

    def test_categorical_imbalanced(self):
        df = pl.DataFrame({"a": ["x"] * 95 + ["y"] * 5})
        alerts = _get_alerts(
            df,
            ProfileConfig(
                imbalance_threshold=0.9,
                text_unique_ratio=1.0,
            ),
        )
        col_alerts = _alerts_for_column(
            alerts,
            "a",
        )
        assert any(a.alert_type == AlertType.IMBALANCED for a in col_alerts)


class TestHighCorrelation:
    def test_triggers_on_correlated_pair(self):
        n = 50
        x = list(range(n))
        df = pl.DataFrame({"a": x, "b": [v * 2 + 1 for v in x]})
        alerts = _get_alerts(
            df,
            ProfileConfig(correlation_threshold=0.8),
        )
        corr_alerts = [a for a in alerts if a.alert_type == AlertType.HIGH_CORRELATION]
        assert len(corr_alerts) >= 1
        alert = corr_alerts[0]
        assert alert.value > 0.8
        assert "column_b" in alert.details
        assert "method" in alert.details

    def test_no_alert_below_threshold(self):
        import random

        random.seed(42)
        df = pl.DataFrame({"a": list(range(50)), "b": [random.random() for _ in range(50)]})
        alerts = _get_alerts(
            df,
            ProfileConfig(correlation_threshold=0.9),
        )
        corr_alerts = [a for a in alerts if a.alert_type == AlertType.HIGH_CORRELATION]
        assert len(corr_alerts) == 0

    def test_details_has_method(self):
        n = 50
        x = list(range(n))
        df = pl.DataFrame({"a": x, "b": [v * 3 for v in x]})
        alerts = _get_alerts(
            df,
            ProfileConfig(correlation_threshold=0.5),
        )
        corr_alerts = [a for a in alerts if a.alert_type == AlertType.HIGH_CORRELATION]
        assert len(corr_alerts) >= 1
        assert corr_alerts[0].details["method"] in ("phik", "pearson")

    def test_no_duplicate_pairs(self):
        n = 50
        x = list(range(n))
        df = pl.DataFrame({"a": x, "b": [v * 2 for v in x], "c": [v * 3 for v in x]})
        alerts = _get_alerts(
            df,
            ProfileConfig(correlation_threshold=0.5),
        )
        corr_alerts = [a for a in alerts if a.alert_type == AlertType.HIGH_CORRELATION]
        pairs = {tuple(sorted((a.column, a.details["column_b"]))) for a in corr_alerts}
        assert len(pairs) == len(corr_alerts)

    def test_single_column_no_alert(self):
        df = pl.DataFrame({"a": list(range(10))})
        alerts = _get_alerts(df)
        corr_alerts = [a for a in alerts if a.alert_type == AlertType.HIGH_CORRELATION]
        assert len(corr_alerts) == 0


class TestUniform:
    def test_triggers_on_uniform_distribution(self):
        df = pl.DataFrame({"cat": ["A", "B", "C", "D"] * 25})
        alerts = _get_alerts(
            df,
            ProfileConfig(
                uniform_pvalue_threshold=0.05,
                text_unique_ratio=1.0,
            ),
        )
        uniform_alerts = [a for a in alerts if a.alert_type == AlertType.UNIFORM]
        assert len(uniform_alerts) == 1
        assert uniform_alerts[0].column == "cat"
        assert uniform_alerts[0].details["test"] == "chi2_gof"
        assert uniform_alerts[0].details["p_value"] > 0.05

    def test_no_alert_on_skewed_distribution(self):
        df = pl.DataFrame({"cat": ["A"] * 90 + ["B"] * 5 + ["C"] * 5})
        alerts = _get_alerts(
            df,
            ProfileConfig(
                uniform_pvalue_threshold=0.05,
                text_unique_ratio=1.0,
                imbalance_threshold=1.0,
            ),
        )
        uniform_alerts = [a for a in alerts if a.alert_type == AlertType.UNIFORM]
        assert len(uniform_alerts) == 0

    def test_details_contains_p_value(self):
        df = pl.DataFrame({"cat": ["X", "Y", "Z"] * 30})
        alerts = _get_alerts(
            df,
            ProfileConfig(
                uniform_pvalue_threshold=0.05,
                text_unique_ratio=1.0,
            ),
        )
        uniform_alerts = [a for a in alerts if a.alert_type == AlertType.UNIFORM]
        assert len(uniform_alerts) == 1
        assert "p_value" in uniform_alerts[0].details
        assert isinstance(uniform_alerts[0].details["p_value"], float)

    def test_single_category_no_alert(self):
        df = pl.DataFrame({"cat": ["A"] * 20})
        alerts = _get_alerts(df)
        uniform_alerts = [a for a in alerts if a.alert_type == AlertType.UNIFORM]
        assert len(uniform_alerts) == 0


class TestCleanData:
    def test_no_alerts_on_clean_data(self):
        df = pl.DataFrame(
            {
                "score": [10, 20, 30, 40, 50, 10, 20, 30, 40, 50],
                "city": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
                "active": [True, False, True, False, True, False, True, False, True, False],
            },
        )
        alerts = _get_alerts(df)
        col_alerts = [
            a for a in alerts if a.column is not None and a.alert_type != AlertType.UNIFORM
        ]
        assert len(col_alerts) == 0


class TestAlertOrder:
    def test_a_higher_value_comes_first_inside_a_type(self):
        df = pl.DataFrame(
            {
                "low": [1, None, 3, 4, 5, 6, 7, 8, 9, 10],
                "high": [None, None, None, None, None, None, None, 8, 9, 10],
                "mid": [None, None, None, 4, 5, 6, 7, 8, 9, 10],
            },
        )
        missing = [a for a in _get_alerts(df) if a.alert_type == AlertType.HIGH_MISSING]
        assert [a.column for a in missing] == ["high", "mid", "low"]

    def test_types_are_grouped_in_name_order(self):
        df = pl.DataFrame(
            {
                "a": [1, 1, 2, 2],
                "b": [None, None, 3, 3],
            },
        )
        names = [a.alert_type.name for a in _get_alerts(df)]
        assert len(set(names)) > 1
        assert names == sorted(names)

    def test_equal_values_are_sorted_by_column_name(self):
        df = pl.DataFrame(
            {
                "b": [1] * 10,
                "a": [2] * 10,
            },
        )
        constant = [a for a in _get_alerts(df) if a.alert_type == AlertType.CONSTANT]
        assert [a.column for a in constant] == ["a", "b"]

    def test_a_report_with_a_target_is_in_order(self):
        report = ProfileReport(
            make_homes(),
            target="price",
        )
        assert report.alerts == sorted(
            report.alerts,
            key=alert_order,
        )
        assert AlertType.TARGET_LEAKAGE in {a.alert_type for a in report.alerts}

    def test_a_nan_value_goes_last_inside_a_type(self):
        alerts = [
            Alert(
                "a",
                AlertType.SKEWED,
                float("nan"),
            ),
            Alert(
                "b",
                AlertType.SKEWED,
                3.0,
            ),
        ]
        assert [a.column for a in sorted(alerts, key=alert_order)] == ["b", "a"]


class TestInfiniteValues:
    def test_infinite_values_raise_the_alert(self):
        df = pl.DataFrame(
            {"x": [1.0, 2.0, float("inf"), 4.0, float("-inf"), 6.0, 7.0, 8.0, 9.0, 10.0]},
        )
        alert = next(a for a in _get_alerts(df) if a.alert_type == AlertType.INFINITE_VALUES)
        assert alert.column == "x"
        assert alert.value == pytest.approx(0.2)
        assert alert.details == {"n_infinite": 2}

    def test_finite_values_raise_nothing(self):
        df = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]})
        assert AlertType.INFINITE_VALUES not in _alert_types(_get_alerts(df))

    def test_an_integer_column_raises_nothing(self):
        df = pl.DataFrame({"x": list(range(10))})
        assert AlertType.INFINITE_VALUES not in _alert_types(_get_alerts(df))

    def test_the_threshold_decides(self):
        df = pl.DataFrame({"x": [1.0, 2.0, float("inf"), 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]})
        loose = _get_alerts(
            df,
            ProfileConfig(infinite_threshold=0.5),
        )
        assert AlertType.INFINITE_VALUES not in _alert_types(loose)


class TestConstantLength:
    def test_fixed_width_codes_raise_the_alert(self):
        df = pl.DataFrame({"zip": ["01234", "02345", "98765", "12345", "54321", "11111"]})
        alert = next(a for a in _get_alerts(df) if a.alert_type == AlertType.CONSTANT_LENGTH)
        assert alert.column == "zip"
        assert alert.value == 5.0

    def test_different_lengths_raise_nothing(self):
        df = pl.DataFrame({"name": ["Al", "Barbara", "Cy", "Dee", "Eve", "Jo"]})
        assert AlertType.CONSTANT_LENGTH not in _alert_types(_get_alerts(df))

    def test_a_constant_column_raises_only_constant(self):
        df = pl.DataFrame({"c": ["abc"] * 6})
        types = _alert_types(_get_alerts(df))
        assert AlertType.CONSTANT in types
        assert AlertType.CONSTANT_LENGTH not in types

    def test_labels_of_one_length_raise_nothing(self):
        df = pl.DataFrame({"flag": ["M", "F", "M", "F", "M", "F", "M", "F"]})
        assert AlertType.CONSTANT_LENGTH not in _alert_types(_get_alerts(df))

    def test_missing_values_are_ignored(self):
        df = pl.DataFrame({"code": ["A1", None, "B2", "C3", None, "D4"]})
        assert AlertType.CONSTANT_LENGTH in _alert_types(_get_alerts(df))

    def test_the_report_lists_both_alerts_in_the_guide(self):
        df = pl.DataFrame({"x": [1.0, float("inf"), 3.0, 4.0], "code": ["A1", "B2", "C3", "D4"]})
        html = ProfileReport(df).to_html()
        assert "Infinite Values" in html
        assert "Constant Length" in html
