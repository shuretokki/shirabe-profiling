from __future__ import annotations

import math

import numpy as np
import pandas as pd
import polars as pl
import pytest
from scipy.stats import kendalltau, pearsonr, spearmanr

from shirabe_profiling.config import ProfileConfig
from shirabe_profiling.correlations import CorrelationResult, _phik_inverse, compute_correlations
from shirabe_profiling.type_inference import infer_types


def _corr(
    df: pl.DataFrame,
    config: ProfileConfig | None = None,
) -> dict[str, CorrelationResult]:
    config = config or ProfileConfig()
    column_types = infer_types(
        df,
        config,
    )
    return compute_correlations(
        df,
        column_types,
        config,
    )


class TestPearsonBasic:
    def test_returns_pearson_key(self, numeric_df: pl.DataFrame):
        result = _corr(numeric_df)
        assert "pearson" in result
        assert isinstance(result["pearson"], CorrelationResult)

    def test_matrix_shape(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["pearson"].matrix
        n_numeric = 3  # age, salary, score
        assert matrix.height == n_numeric
        assert matrix.width == n_numeric + 1  # +1 for "column" label

    def test_diagonal_is_one(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["pearson"].matrix
        for row in matrix.iter_rows(named=True):
            col_name = row["column"]
            assert row[col_name] == pytest.approx(1.0)

    def test_symmetric(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["pearson"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        cols = [c for c in matrix.columns if c != "column"]
        for a in cols:
            for b in cols:
                assert rows[a][b] == pytest.approx(
                    rows[b][a],
                    abs=1e-10,
                )

    def test_values_in_range(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["pearson"].matrix
        for row in matrix.iter_rows(named=True):
            for col in matrix.columns:
                if col == "column":
                    continue
                assert -1.0 <= row[col] <= 1.0

    def test_perfect_correlation(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10]})
        matrix = _corr(df)["pearson"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(1.0)

    def test_negative_correlation(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 8, 6, 4, 2]})
        matrix = _corr(df)["pearson"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(-1.0)

    def test_columns_sorted(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["pearson"].matrix
        col_labels = matrix["column"].to_list()
        assert col_labels == sorted(col_labels)

    def test_pvalues_present(self, numeric_df: pl.DataFrame):
        result = _corr(numeric_df)["pearson"]
        assert result.pvalues is not None
        assert result.pvalues.height == result.matrix.height
        for row in result.pvalues.iter_rows(named=True):
            for col in result.pvalues.columns:
                if col == "column":
                    continue
                assert 0.0 <= row[col] <= 1.0


class TestSpearmanBasic:
    def test_returns_spearman_key(self, numeric_df: pl.DataFrame):
        result = _corr(numeric_df)
        assert "spearman" in result
        assert isinstance(result["spearman"], CorrelationResult)

    def test_matrix_shape(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["spearman"].matrix
        n_numeric = 3
        assert matrix.height == n_numeric
        assert matrix.width == n_numeric + 1

    def test_diagonal_is_one(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["spearman"].matrix
        for row in matrix.iter_rows(named=True):
            assert row[row["column"]] == pytest.approx(1.0)

    def test_symmetric(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["spearman"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        cols = [c for c in matrix.columns if c != "column"]
        for a in cols:
            for b in cols:
                assert rows[a][b] == pytest.approx(
                    rows[b][a],
                    abs=1e-10,
                )

    def test_values_in_range(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["spearman"].matrix
        for row in matrix.iter_rows(named=True):
            for col in matrix.columns:
                if col == "column":
                    continue
                assert -1.0 <= row[col] <= 1.0

    def test_perfect_monotonic(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10]})
        matrix = _corr(df)["spearman"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(1.0)

    def test_negative_monotonic(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 8, 6, 4, 2]})
        matrix = _corr(df)["spearman"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(-1.0)

    def test_nonlinear_monotonic(self):
        """Spearman captures monotonic non-linear relationships better than Pearson."""
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [1, 4, 9, 16, 25]})
        result = _corr(df)
        spearman = result["spearman"].matrix
        pearson = result["pearson"].matrix
        sp_rows = {r["column"]: r for r in spearman.iter_rows(named=True)}
        pe_rows = {r["column"]: r for r in pearson.iter_rows(named=True)}
        assert sp_rows["a"]["b"] == pytest.approx(1.0)
        assert pe_rows["a"]["b"] < 1.0

    def test_pvalues_present(self, numeric_df: pl.DataFrame):
        result = _corr(numeric_df)["spearman"]
        assert result.pvalues is not None
        assert result.pvalues.height == result.matrix.height
        for row in result.pvalues.iter_rows(named=True):
            for col in result.pvalues.columns:
                if col == "column":
                    continue
                assert 0.0 <= row[col] <= 1.0

    def test_perfect_correlation_pvalue_zero(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10]})
        result = _corr(df)["spearman"]
        rows = {r["column"]: r for r in result.pvalues.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(
            0.0,
            abs=1e-6,
        )

    def test_columns_sorted(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["spearman"].matrix
        col_labels = matrix["column"].to_list()
        assert col_labels == sorted(col_labels)


class TestKendallBasic:
    def test_returns_kendall_key(self, numeric_df: pl.DataFrame):
        result = _corr(numeric_df)
        assert "kendall" in result
        assert isinstance(result["kendall"], CorrelationResult)

    def test_matrix_shape(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["kendall"].matrix
        n_numeric = 3
        assert matrix.height == n_numeric
        assert matrix.width == n_numeric + 1

    def test_diagonal_is_one(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["kendall"].matrix
        for row in matrix.iter_rows(named=True):
            assert row[row["column"]] == pytest.approx(1.0)

    def test_symmetric(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["kendall"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        cols = [c for c in matrix.columns if c != "column"]
        for a in cols:
            for b in cols:
                assert rows[a][b] == pytest.approx(
                    rows[b][a],
                    abs=1e-10,
                )

    def test_values_in_range(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["kendall"].matrix
        for row in matrix.iter_rows(named=True):
            for col in matrix.columns:
                if col == "column":
                    continue
                assert -1.0 <= row[col] <= 1.0

    def test_perfect_concordance(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 4, 6, 8, 10]})
        matrix = _corr(df)["kendall"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(1.0)

    def test_perfect_discordance(self):
        df = pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 8, 6, 4, 2]})
        matrix = _corr(df)["kendall"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(-1.0)

    def test_with_ties(self):
        """Kendall tau-b handles tied values correctly."""
        df = pl.DataFrame({"a": [1, 2, 2, 3, 4], "b": [1, 2, 2, 3, 5]})
        matrix = _corr(df)["kendall"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert 0.0 < rows["a"]["b"] <= 1.0

    def test_pvalues_present(self, numeric_df: pl.DataFrame):
        result = _corr(numeric_df)["kendall"]
        assert result.pvalues is not None
        assert result.pvalues.height == result.matrix.height
        for row in result.pvalues.iter_rows(named=True):
            for col in result.pvalues.columns:
                if col == "column":
                    continue
                assert 0.0 <= row[col] <= 1.0

    def test_columns_sorted(self, numeric_df: pl.DataFrame):
        matrix = _corr(numeric_df)["kendall"].matrix
        col_labels = matrix["column"].to_list()
        assert col_labels == sorted(col_labels)

    def test_matches_scipy_reference(self):
        """Our matrix values must match scipy.stats.kendalltau directly."""
        df = pl.DataFrame({"a": [1, 2, 2, 3, 4], "b": [1, 3, 2, 4, 5]})
        matrix = _corr(df)["kendall"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        expected_tau, _ = kendalltau(
            df["a"].to_list(),
            df["b"].to_list(),
        )
        assert rows["a"]["b"] == pytest.approx(
            expected_tau,
            abs=1e-10,
        )

    def test_perfect_concordance_pvalue_near_zero(self):
        df = pl.DataFrame({"a": list(range(20)), "b": list(range(20))})
        result = _corr(df)["kendall"]
        rows = {r["column"]: r for r in result.pvalues.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(
            0.0,
            abs=1e-6,
        )

    def test_constant_column_nan(self):
        """Kendall of a constant vs variable should be NaN (zero variance)."""
        import math

        df = pl.DataFrame(
            {
                "a": [1, 1, 1, 1, 1],
                "b": [1, 2, 3, 4, 5],
                "c": [5, 4, 3, 2, 1],
            },
        )
        result = _corr(df)["kendall"]
        rows = {r["column"]: r for r in result.matrix.iter_rows(named=True)}
        assert math.isnan(rows["a"]["b"])
        assert math.isnan(rows["a"]["c"])


class TestCramersVBasic:
    @pytest.fixture()
    def cat_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "color": ["red", "blue", "red", "green", "blue"] * 20,
                "shape": ["circle", "square", "circle", "triangle", "square"] * 20,
                "size": ["S", "M", "L", "S", "M"] * 20,
            },
        )

    def test_returns_cramers_v_key(self, cat_df: pl.DataFrame):
        result = _corr(cat_df)
        assert "cramers_v" in result
        assert isinstance(result["cramers_v"], CorrelationResult)

    def test_matrix_shape(self, cat_df: pl.DataFrame):
        matrix = _corr(cat_df)["cramers_v"].matrix
        assert matrix.height == 3
        assert matrix.width == 3 + 1

    def test_diagonal_is_one(self, cat_df: pl.DataFrame):
        matrix = _corr(cat_df)["cramers_v"].matrix
        for row in matrix.iter_rows(named=True):
            assert row[row["column"]] == pytest.approx(1.0)

    def test_symmetric(self, cat_df: pl.DataFrame):
        matrix = _corr(cat_df)["cramers_v"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        cols = [c for c in matrix.columns if c != "column"]
        for a in cols:
            for b in cols:
                assert rows[a][b] == pytest.approx(
                    rows[b][a],
                    abs=1e-10,
                )

    def test_values_in_range(self, cat_df: pl.DataFrame):
        matrix = _corr(cat_df)["cramers_v"].matrix
        for row in matrix.iter_rows(named=True):
            for col in matrix.columns:
                if col == "column":
                    continue
                assert 0.0 <= row[col] <= 1.0

    def test_no_pvalues(self, cat_df: pl.DataFrame):
        result = _corr(cat_df)["cramers_v"]
        assert result.pvalues is None

    def test_perfect_association(self):
        """Identical columns → V = 1.0."""
        df = pl.DataFrame(
            {
                "a": ["x", "y", "z"] * 10,
                "b": ["x", "y", "z"] * 10,
            },
        )
        matrix = _corr(df)["cramers_v"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(1.0)

    def test_no_association(self):
        """Independent columns → V ≈ 0."""
        import random

        random.seed(42)
        a = [random.choice(["x", "y", "z"]) for _ in range(1000)]
        b = [random.choice(["p", "q", "r"]) for _ in range(1000)]
        df = pl.DataFrame({"a": a, "b": b})
        matrix = _corr(df)["cramers_v"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] < 0.1

    def test_columns_sorted(self, cat_df: pl.DataFrame):
        matrix = _corr(cat_df)["cramers_v"].matrix
        col_labels = matrix["column"].to_list()
        assert col_labels == sorted(col_labels)

    def test_single_categorical_column_skips(self):
        df = pl.DataFrame({"a": [1, 2, 3], "cat": ["x", "y", "z"]})
        result = _corr(df)
        assert "cramers_v" not in result

    def test_mixed_df_cramers_only_categorical(self):
        df = pl.DataFrame(
            {
                "num1": [1, 2, 3, 4, 5],
                "num2": [5, 4, 3, 2, 1],
                "cat1": ["a", "b", "a", "b", "a"],
                "cat2": ["x", "y", "x", "y", "x"],
            },
        )
        result = _corr(df)
        assert "pearson" in result
        assert "cramers_v" in result
        cv_cols = result["cramers_v"].matrix["column"].to_list()
        assert "num1" not in cv_cols
        assert "cat1" in cv_cols

    def test_matches_scipy_reference(self):
        """Our Cramér's V must match scipy chi2_contingency calculation."""
        import numpy as np
        from scipy.stats import chi2_contingency

        df = pl.DataFrame(
            {
                "a": ["x", "x", "y", "y", "z", "z"] * 10,
                "b": ["p", "q", "p", "r", "q", "r"] * 10,
            },
        )
        our_v = _corr(df)["cramers_v"].matrix
        rows = {r["column"]: r for r in our_v.iter_rows(named=True)}

        ct = pd.crosstab(
            pd.Series(df["a"].to_list()),
            pd.Series(df["b"].to_list()),
        )
        chi2, _, _, _ = chi2_contingency(ct)
        n_obs = ct.values.sum()
        min_dim = min(ct.shape) - 1
        expected_v = np.sqrt(chi2 / (n_obs * min_dim))

        assert rows["a"]["b"] == pytest.approx(
            expected_v,
            abs=1e-4,
        )


class TestPhiKBasic:
    @pytest.fixture()
    def mixed_phik_df(self) -> pl.DataFrame:
        import random

        random.seed(42)
        n = 200
        return pl.DataFrame(
            {
                "num1": [
                    random.gauss(
                        0,
                        1,
                    )
                    for _ in range(n)
                ],
                "num2": [
                    random.gauss(
                        0,
                        1,
                    )
                    for _ in range(n)
                ],
                "cat1": [random.choice(["a", "b", "c"]) for _ in range(n)],
                "cat2": [random.choice(["x", "y", "z"]) for _ in range(n)],
            },
        )

    def test_returns_phik_key(self, mixed_phik_df: pl.DataFrame):
        result = _corr(mixed_phik_df)
        assert "phik" in result
        assert isinstance(result["phik"], CorrelationResult)

    def test_matrix_shape(self, mixed_phik_df: pl.DataFrame):
        matrix = _corr(mixed_phik_df)["phik"].matrix
        assert matrix.height == 4
        assert matrix.width == 4 + 1

    def test_diagonal_is_one(self, mixed_phik_df: pl.DataFrame):
        matrix = _corr(mixed_phik_df)["phik"].matrix
        for row in matrix.iter_rows(named=True):
            assert row[row["column"]] == pytest.approx(1.0)

    def test_symmetric(self, mixed_phik_df: pl.DataFrame):
        matrix = _corr(mixed_phik_df)["phik"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        cols = [c for c in matrix.columns if c != "column"]
        for a in cols:
            for b in cols:
                assert rows[a][b] == pytest.approx(
                    rows[b][a],
                    abs=1e-10,
                )

    def test_values_in_range(self, mixed_phik_df: pl.DataFrame):
        matrix = _corr(mixed_phik_df)["phik"].matrix
        for row in matrix.iter_rows(named=True):
            for col in matrix.columns:
                if col == "column":
                    continue
                assert 0.0 <= row[col] <= 1.0

    def test_no_pvalues(self, mixed_phik_df: pl.DataFrame):
        result = _corr(mixed_phik_df)["phik"]
        assert result.pvalues is None

    def test_perfect_association(self):
        """Identical columns → phik ≈ 1.0."""
        df = pl.DataFrame(
            {
                "a": ["x", "y", "z"] * 30,
                "b": ["x", "y", "z"] * 30,
            },
        )
        matrix = _corr(df)["phik"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] == pytest.approx(
            1.0,
            abs=0.05,
        )

    def test_independent_columns_near_zero(self):
        """Independent columns → phik ≈ 0."""
        import random

        random.seed(99)
        n = 2000
        df = pl.DataFrame(
            {
                "a": [random.choice(["x", "y", "z"]) for _ in range(n)],
                "b": [random.choice(["p", "q", "r"]) for _ in range(n)],
            },
        )
        matrix = _corr(df)["phik"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert rows["a"]["b"] < 0.1

    def test_mixed_numeric_categorical(self):
        """Phi K works across numeric × categorical pairs."""
        import random

        random.seed(42)
        n = 200
        cats = [random.choice(["a", "b"]) for _ in range(n)]
        centers = {"a": 1.0, "b": 5.0}
        nums = [
            centers[c]
            + random.gauss(
                0,
                0.1,
            )
            for c in cats
        ]
        df = pl.DataFrame({"num": nums, "cat": cats})
        result = _corr(df)
        assert "phik" in result
        rows = {r["column"]: r for r in result["phik"].matrix.iter_rows(named=True)}
        assert rows["cat"]["num"] > 0.3

    def test_columns_sorted(self, mixed_phik_df: pl.DataFrame):
        matrix = _corr(mixed_phik_df)["phik"].matrix
        col_labels = matrix["column"].to_list()
        assert col_labels == sorted(col_labels)

    def test_includes_all_column_types(self, mixed_phik_df: pl.DataFrame):
        """Phi K matrix includes both numeric and categorical columns."""
        matrix = _corr(mixed_phik_df)["phik"].matrix
        col_labels = matrix["column"].to_list()
        assert "num1" in col_labels
        assert "cat1" in col_labels

    def test_matches_phik_library(self):
        """Our values must match phik library with noise correction."""
        import numpy as np
        from phik import phik_matrix as phik_matrix_fn

        np.random.seed(42)
        n = 5000
        data = {
            "num1": np.random.randn(n).tolist(),
            "num2": (np.random.randn(n) * 2).tolist(),
            "cat1": np.random.choice(
                ["a", "b", "c"],
                n,
            ).tolist(),
            "cat2": np.random.choice(
                ["x", "y", "z"],
                n,
            ).tolist(),
        }
        our_result = _corr(pl.DataFrame(data))["phik"].matrix
        our_rows = {r["column"]: r for r in our_result.iter_rows(named=True)}

        phik_ref = phik_matrix_fn(
            pd.DataFrame(data),
            interval_cols=["num1", "num2"],
            verbose=False,
            njobs=1,
            noise_correction=True,
        )
        for a in ["cat1", "cat2", "num1", "num2"]:
            for b in ["cat1", "cat2", "num1", "num2"]:
                if a == b:
                    continue
                assert our_rows[a][b] == pytest.approx(
                    phik_ref.loc[a, b],
                    abs=0.01,
                ), f"{a}×{b}: {our_rows[a][b]} vs {phik_ref.loc[a, b]}"


class TestCorrelationEdgeCases:
    def test_single_numeric_single_text(self):
        """1 numeric + 1 text (high unique ratio) → no pearson, no cramers_v, no phik."""
        df = pl.DataFrame({"a": [1, 2, 3], "city": ["x", "y", "z"]})
        result = _corr(df)
        assert "pearson" not in result
        assert "cramers_v" not in result
        assert "phik" not in result

    def test_single_numeric_single_categorical_has_phik(self):
        """1 numeric + 1 categorical (low unique ratio) → phik only."""
        df = pl.DataFrame(
            {
                "a": list(range(20)),
                "cat": ["x", "y"] * 10,
            },
        )
        result = _corr(df)
        assert "pearson" not in result
        assert "phik" in result

    def test_no_numeric_columns_has_cramers_v(self, categorical_df: pl.DataFrame):
        result = _corr(categorical_df)
        assert "pearson" not in result
        assert "cramers_v" in result

    def test_overview_mode_skips(self, numeric_df: pl.DataFrame):
        config = ProfileConfig(mode="overview")
        result = _corr(
            numeric_df,
            config,
        )
        assert result == {}

    def test_with_nulls(self):
        df = pl.DataFrame(
            {
                "a": [1.0, 2.0, None, 4.0, 5.0],
                "b": [None, 4.0, 6.0, 8.0, 10.0],
            },
        )
        result = _corr(df)
        assert "pearson" in result
        matrix = result["pearson"].matrix
        rows = {r["column"]: r for r in matrix.iter_rows(named=True)}
        assert -1.0 <= rows["a"]["b"] <= 1.0

    def test_mixed_df_only_numeric(self, mixed_df: pl.DataFrame):
        result = _corr(mixed_df)
        assert "pearson" in result
        matrix = result["pearson"].matrix
        col_labels = matrix["column"].to_list()
        for label in col_labels:
            assert label in ("age", "id", "salary")

    def test_empty_dataframe(self, empty_df: pl.DataFrame):
        result = _corr(empty_df)
        assert result == {}


class TestWideData:
    @staticmethod
    def _wide_frame(
        numeric: int,
        categorical: int,
        rows: int = 400,
    ) -> pl.DataFrame:
        rng = np.random.default_rng(5)
        base = rng.normal(size=rows)
        data: dict[str, object] = {}
        for i in range(numeric):
            values = base * (i % 4) * 0.4 + rng.normal(size=rows)
            data[f"n{i:02d}"] = np.where(
                rng.random(rows) < 0.05,
                np.nan,
                values,
            )
        for i in range(categorical):
            data[f"c{i:02d}"] = rng.choice(
                ["a", "b", "c", "d"][: 2 + i % 3],
                rows,
            )
        frame = pl.DataFrame(data)
        return frame.with_columns(pl.col(c).fill_nan(None) for c in data if c.startswith("n"))

    def test_every_method_covers_every_column(self):
        result = _corr(
            self._wide_frame(
                30,
                8,
            ),
        )

        assert result["pearson"].matrix.height == 30
        assert result["kendall"].matrix.height == 30
        assert result["cramers_v"].matrix.height == 8
        assert result["phik"].matrix.height == 38

    def test_kendall_is_skipped_above_the_column_limit(self):
        frame = self._wide_frame(
            12,
            0,
        )

        skipped = _corr(
            frame,
            ProfileConfig(kendall_max_columns=11),
        )
        kept = _corr(
            frame,
            ProfileConfig(kendall_max_columns=12),
        )

        assert "kendall" not in skipped
        assert "pearson" in skipped
        assert "kendall" in kept

    def test_kendall_uses_a_sample_on_long_data(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "shirabe_profiling.correlations.KENDALL_MAX_ROWS",
            60,
        )

        result = _corr(
            self._wide_frame(
                3,
                0,
                rows=300,
            ),
        )

        values = result["kendall"].matrix.drop("column").to_numpy()
        assert np.all(np.abs(values) <= 1.0)

    def test_kendall_column_limit_is_validated(self):
        with pytest.raises(
            ValueError,
            match="kendall_max_columns",
        ):
            ProfileConfig(kendall_max_columns=1)


class TestPairwiseNulls:
    def test_pearson_uses_only_rows_where_both_values_exist(self):
        rng = np.random.default_rng(1)
        a = rng.normal(size=200)
        b = a * 0.5 + rng.normal(size=200)
        c = rng.normal(size=200)
        df = pl.DataFrame({"a": a, "b": b, "c": c}).with_columns(
            pl.when(pl.int_range(pl.len()) % 7 == 0).then(None).otherwise(pl.col("a")).alias("a"),
            pl.when(pl.int_range(pl.len()) % 5 == 0).then(None).otherwise(pl.col("b")).alias("b"),
        )

        result = _corr(df)["pearson"]
        rows = {r["column"]: r for r in result.matrix.iter_rows(named=True)}
        pvalues = {r["column"]: r for r in result.pvalues.iter_rows(named=True)}

        complete = df.drop_nulls(["a", "b"])
        expected = pearsonr(
            complete["a"].to_numpy(),
            complete["b"].to_numpy(),
        )
        assert rows["a"]["b"] == pytest.approx(
            expected.statistic,
            abs=1e-10,
        )
        assert pvalues["a"]["b"] == pytest.approx(
            expected.pvalue,
            abs=1e-10,
        )

    def test_spearman_matches_scipy_without_nulls(self):
        rng = np.random.default_rng(2)
        a = rng.normal(size=150)
        df = pl.DataFrame({"a": a, "b": a**3 + rng.normal(size=150)})

        result = _corr(df)["spearman"]
        rows = {r["column"]: r for r in result.matrix.iter_rows(named=True)}

        expected = spearmanr(
            df["a"].to_numpy(),
            df["b"].to_numpy(),
        )
        assert rows["a"]["b"] == pytest.approx(
            expected.statistic,
            abs=1e-10,
        )

    def test_constant_column_gives_nan_not_an_error(self):
        df = pl.DataFrame(
            {"a": [1.0, 2.0, 3.0, 4.0], "flat": [5.0] * 4, "b": [2.0, 1.0, 4.0, 3.0]},
        )

        rows = {r["column"]: r for r in _corr(df)["pearson"].matrix.iter_rows(named=True)}

        assert math.isnan(rows["a"]["flat"])
        assert rows["flat"]["flat"] == pytest.approx(1.0)
        assert not math.isnan(rows["a"]["b"])


class TestPhiKCurve:
    @pytest.mark.parametrize(
        "shape",
        [(2, 2), (3, 3), (10, 10), (4, 7), (10, 3)],
    )
    def test_curve_matches_the_library_solver(self, shape: tuple[int, int]):
        from phik.bivariate import phik_from_chi2

        rows, cols = shape
        n = 2000
        pedestal = (rows - 1) * (cols - 1)
        top = n * min(rows - 1, cols - 1)
        for scaled in (0.05, 0.3, 0.6, 0.9):
            chi2 = pedestal + scaled * (top - pedestal)
            expected = phik_from_chi2(
                chi2,
                n,
                nx=rows,
                ny=cols,
                pedestal=pedestal,
            )
            assert _phik_inverse(
                rows,
                cols,
            )(scaled) == pytest.approx(
                expected,
                abs=2e-3,
            )
