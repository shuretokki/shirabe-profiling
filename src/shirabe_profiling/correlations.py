# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Correlation matrices.

Pearson and Spearman come from one matrix product over all numeric columns.
Phi K and Cramér's V encode every column to integer codes once, then count each pair with numpy.
Kendall tau-b uses scipy's merge sort on a capped random sample, because its cost grows fastest.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from typing import TYPE_CHECKING, cast

import numpy as np
import polars as pl
from phik.bivariate import chi2_from_phik, phik_from_chi2
from scipy import stats
from scipy.interpolate import PchipInterpolator

from shirabe_profiling.config import ProfileConfig
from shirabe_profiling.type_inference import ColumnType

if TYPE_CHECKING:
    from collections.abc import Callable

KENDALL_MAX_ROWS = 10_000
_KENDALL_WORKERS = 2
_PHIK_BINS = 10
_PHIK_CURVE_POINTS = 129
_DENSE_TABLE_LIMIT = 4096
_MAX_TABLE_CELLS = 4_000_000
_MIN_SPREAD = 1e-12


@dataclass(
    frozen=True,
    slots=True,
)
class CorrelationResult:
    """A correlation matrix with optional p-values."""

    matrix: pl.DataFrame
    pvalues: pl.DataFrame | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class Coded:
    """One column as integer codes. A code of -1 marks a missing value."""

    codes: np.ndarray
    size: int


def compute_correlations(
    df: pl.DataFrame,
    column_types: dict[str, ColumnType],
    config: ProfileConfig | None = None,
) -> dict[str, CorrelationResult]:
    """Compute correlation matrices.

    Returns a dict keyed by method name (e.g. "pearson").
    Empty dict when fewer than 2 numeric columns or overview mode.
    Kendall is skipped when the data has more numeric columns than kendall_max_columns.
    """
    settings = config or ProfileConfig()
    if settings.is_overview:
        return {}

    if df.height < 2:
        return {}

    numeric_cols = sorted(col for col, ct in column_types.items() if ct is ColumnType.NUMERIC)
    categorical_cols = sorted(
        col for col, ct in column_types.items() if ct is ColumnType.CATEGORICAL
    )
    all_cols = sorted(numeric_cols + categorical_cols)

    result: dict[str, CorrelationResult] = {}
    coded: dict[str, Coded] = {}

    if len(all_cols) >= 2:
        coded = _encode_columns(
            df,
            all_cols,
            frozenset(numeric_cols),
        )
        result["phik"] = _coded_matrix(
            coded,
            all_cols,
            phik_value,
        )

    if len(numeric_cols) >= 2:
        values = numeric_matrix(
            df,
            numeric_cols,
        )
        result["pearson"] = _linear_result(
            numeric_cols,
            values,
        )
        result["spearman"] = _linear_result(
            numeric_cols,
            rank_columns(values),
        )
        if len(numeric_cols) <= settings.kendall_max_columns:
            result["kendall"] = _kendall_result(
                df,
                numeric_cols,
                settings.interaction_sample_seed,
            )

    if len(categorical_cols) >= 2:
        result["cramers_v"] = _coded_matrix(
            coded,
            categorical_cols,
            _cramers_v_value,
        )

    return result


def _matrix_frame(
    columns: list[str],
    data: np.ndarray,
) -> pl.DataFrame:
    return pl.DataFrame(
        {"column": columns, **{name: data[:, j] for j, name in enumerate(columns)}},
    )


def _result(
    columns: list[str],
    estimates: np.ndarray,
    pvalues: np.ndarray | None,
) -> CorrelationResult:
    """Build the result and fix the diagonal: every column matches itself exactly."""
    np.fill_diagonal(
        estimates,
        1.0,
    )
    if pvalues is not None:
        np.fill_diagonal(
            pvalues,
            0.0,
        )
    return CorrelationResult(
        matrix=_matrix_frame(
            columns,
            estimates,
        ),
        pvalues=_matrix_frame(
            columns,
            pvalues,
        )
        if pvalues is not None
        else None,
    )


# -- Pearson and Spearman --------------------------------------------------


def numeric_matrix(
    df: pl.DataFrame,
    columns: list[str],
) -> np.ndarray:
    """Return the columns as a float matrix. Missing and infinite values become NaN."""
    matrix = df.select(pl.col(name).cast(pl.Float64) for name in columns).to_numpy()
    return np.where(
        np.isfinite(matrix),
        matrix,
        np.nan,
    )


def rank_columns(values: np.ndarray) -> np.ndarray:
    """Replace each column by its average ranks. Missing values stay missing."""
    ranks = np.full_like(
        values,
        np.nan,
    )
    for j in range(values.shape[1]):
        valid = np.isfinite(values[:, j])
        if valid.any():
            ranks[valid, j] = stats.rankdata(
                values[valid, j],
                method="average",
            )
    return ranks


def _linear_result(
    columns: list[str],
    values: np.ndarray,
) -> CorrelationResult:
    estimates, counts = pairwise_pearson(values)
    return _result(
        columns,
        estimates,
        _t_pvalues(
            estimates,
            counts,
        ),
    )


def pairwise_pearson(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pearson r for every column pair, using only the rows where both values exist."""
    valid = np.isfinite(values)
    present = valid.astype(np.float64)
    column_counts = present.sum(axis=0)
    means = np.where(
        valid,
        values,
        0.0,
    ).sum(axis=0) / np.maximum(
        column_counts,
        1.0,
    )
    centered = np.where(
        valid,
        values - means,
        0.0,
    )

    counts = present.T @ present
    sum_x = centered.T @ present
    sum_y = sum_x.T
    sum_xx = (centered * centered).T @ present
    sum_yy = sum_xx.T
    sum_xy = centered.T @ centered

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        cov = sum_xy - sum_x * sum_y / counts
        var_x = sum_xx - sum_x**2 / counts
        var_y = sum_yy - sum_y**2 / counts
        flat = (
            var_x
            <= _MIN_SPREAD
            * np.maximum(
                sum_xx,
                1e-300,
            )
        ) | (
            var_y
            <= _MIN_SPREAD
            * np.maximum(
                sum_yy,
                1e-300,
            )
        )
        estimates = np.clip(
            cov / np.sqrt(var_x * var_y),
            -1.0,
            1.0,
        )
    estimates[flat | (counts < 2)] = np.nan
    return estimates, counts


def _t_pvalues(
    estimates: np.ndarray,
    counts: np.ndarray,
) -> np.ndarray:
    """Two-sided p-values from the t distribution, as scipy computes them."""
    degrees = counts - 2
    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        t_stat = estimates * np.sqrt(degrees / (1.0 - estimates**2))
        pvalues = 2.0 * stats.t.sf(
            np.abs(t_stat),
            degrees,
        )
    pvalues = np.where(
        np.abs(estimates) >= 1.0,
        0.0,
        pvalues,
    )
    pvalues[degrees < 1] = np.nan
    pvalues[np.isnan(estimates)] = np.nan
    return pvalues


# -- Kendall ---------------------------------------------------------------


def _kendall_result(
    df: pl.DataFrame,
    columns: list[str],
    seed: int,
) -> CorrelationResult:
    frame = df.select(columns)
    if frame.height > KENDALL_MAX_ROWS:
        frame = frame.sample(
            KENDALL_MAX_ROWS,
            seed=seed,
        )
    arrays = [
        numeric_matrix(
            frame,
            [name],
        )[:, 0]
        for name in columns
    ]

    size = len(columns)
    estimates = np.zeros((size, size))
    pvalues = np.zeros((size, size))
    pairs = list(
        combinations(
            range(size),
            2,
        ),
    )
    with ThreadPoolExecutor(max_workers=_KENDALL_WORKERS) as pool:
        outcomes = pool.map(
            lambda pair: _kendall_pair(
                arrays[pair[0]],
                arrays[pair[1]],
            ),
            pairs,
        )
        for (i, j), (tau, pvalue) in zip(pairs, outcomes, strict=True):
            estimates[i, j] = estimates[j, i] = tau
            pvalues[i, j] = pvalues[j, i] = pvalue
    return _result(
        columns,
        estimates,
        pvalues,
    )


def _kendall_pair(
    a: np.ndarray,
    b: np.ndarray,
) -> tuple[float, float]:
    """Kendall tau-b for one pair, using the rows where both values exist."""
    keep = np.isfinite(a) & np.isfinite(b)
    if keep.sum() < 2:
        return 0.0, 1.0
    x, y = a[keep], b[keep]
    if x.min() == x.max() or y.min() == y.max():
        return float("nan"), float("nan")
    tau, pvalue = cast(
        "tuple[float, float]",
        stats.kendalltau(
            x,
            y,
        ),
    )
    return float(tau), float(pvalue)


# -- Phi K and Cramér's V --------------------------------------------------


def _encode_columns(
    df: pl.DataFrame,
    columns: list[str],
    numeric: frozenset[str],
) -> dict[str, Coded]:
    """Encode each column once: numeric columns into equal-width bins, others into categories."""
    coded: dict[str, Coded] = {}
    for name in columns:
        if name in numeric:
            coded[name] = bin_numeric(
                numeric_matrix(
                    df,
                    [name],
                )[:, 0],
            )
        else:
            coded[name] = encode_categories(df[name])
    return coded


def bin_numeric(values: np.ndarray) -> Coded:
    valid = np.isfinite(values)
    codes = np.full(
        values.shape,
        -1,
        dtype=np.int64,
    )
    if not valid.any():
        return Coded(
            codes,
            0,
        )

    low, high = values[valid].min(), values[valid].max()
    if low == high:
        codes[valid] = 0
        return Coded(
            codes,
            1,
        )

    edges = np.linspace(
        low,
        high,
        _PHIK_BINS + 1,
    )[1:-1]
    codes[valid] = np.digitize(
        values[valid],
        edges,
        right=True,
    )
    return Coded(
        codes,
        _PHIK_BINS,
    )


def encode_categories(series: pl.Series) -> Coded:
    physical = series.cast(pl.String).cast(pl.Categorical).to_physical()
    codes = np.array(
        physical.fill_null(-1).cast(pl.Int64).to_numpy(),
        dtype=np.int64,
    )
    valid = codes >= 0
    if not valid.any():
        return Coded(
            codes,
            0,
        )
    unique, inverse = np.unique(
        codes[valid],
        return_inverse=True,
    )
    codes[valid] = inverse
    return Coded(
        codes,
        len(unique),
    )


def _coded_matrix(
    coded: dict[str, Coded],
    columns: list[str],
    value_fn: Callable[[Coded, Coded], float],
) -> CorrelationResult:
    size = len(columns)
    estimates = np.zeros((size, size))
    for i, j in combinations(
        range(size),
        2,
    ):
        estimates[i, j] = estimates[j, i] = value_fn(
            coded[columns[i]],
            coded[columns[j]],
        )
    return _result(
        columns,
        estimates,
        None,
    )


def _contingency(
    a: Coded,
    b: Coded,
) -> tuple[np.ndarray | None, int]:
    """Count the pairs of codes. Returns None when the table is too small or too large."""
    keep = (a.codes >= 0) & (b.codes >= 0)
    n = int(keep.sum())
    if n < 2:
        return None, n

    first, second = a.codes[keep], b.codes[keep]
    if a.size * b.size <= _DENSE_TABLE_LIMIT:
        table = np.bincount(
            first * b.size + second,
            minlength=a.size * b.size,
        )
        table = table.reshape(
            a.size,
            b.size,
        )
    else:
        combined = first * b.size + second
        unique, counts = np.unique(
            combined,
            return_counts=True,
        )
        rows, row_index = np.unique(
            unique // b.size,
            return_inverse=True,
        )
        cols, col_index = np.unique(
            unique % b.size,
            return_inverse=True,
        )
        if len(rows) * len(cols) > _MAX_TABLE_CELLS:
            return None, n
        table = np.zeros(
            (len(rows), len(cols)),
            dtype=np.int64,
        )
        table[row_index, col_index] = counts

    table = table[table.sum(axis=1) > 0][:, table.sum(axis=0) > 0]
    return table, n


def _chi_square(table: np.ndarray) -> float:
    expected = (
        np.outer(
            table.sum(axis=1),
            table.sum(axis=0),
        )
        / table.sum()
    )
    return float(((table - expected) ** 2 / expected).sum())


def _cramers_v_value(
    a: Coded,
    b: Coded,
) -> float:
    table, n = _contingency(
        a,
        b,
    )
    if table is None or min(table.shape) < 2:
        return float("nan")
    chi2 = _chi_square(table)
    return float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))


@lru_cache(maxsize=256)
def _phik_inverse(
    rows: int,
    cols: int,
) -> PchipInterpolator:
    """Map a scaled chi-square (0 to 1) to a Phi K value for one table shape.

    The phik library solves this mapping again for every pair.
    It depends only on the table shape, so one curve per shape is enough.
    Swapping the rows and columns gives the same curve.
    The value at 1.0 is the largest possible chi-square, so it sets the scale.
    """
    rho = np.linspace(
        0.0,
        1.0,
        _PHIK_CURVE_POINTS,
    )
    raw = np.array(
        [
            chi2_from_phik(
                r,
                1,
                scale=1.0,
                nx=rows,
                ny=cols,
                pedestal=0,
            )
            for r in rho
        ],
    )
    scaled = np.maximum.accumulate(raw / raw[-1])
    keep = np.concatenate(([True], np.diff(scaled) > 1e-15))
    return PchipInterpolator(
        scaled[keep],
        rho[keep],
    )


def phik_value(
    a: Coded,
    b: Coded,
) -> float:
    table, n = _contingency(
        a,
        b,
    )
    if table is None or min(table.shape) < 2:
        return 0.0
    chi2 = _chi_square(table)
    rows, cols = table.shape
    pedestal = (rows - 1) * (cols - 1)
    top = n * min(rows - 1, cols - 1)
    if chi2 <= pedestal:
        return 0.0
    if top <= pedestal:
        return _phik_from_library(
            chi2,
            n,
            rows,
            cols,
            pedestal,
        )
    if chi2 >= top:
        return 1.0
    scaled = (chi2 - pedestal) / (top - pedestal)
    curve = _phik_inverse(
        min(rows, cols),
        max(rows, cols),
    )
    return float(
        np.clip(
            curve(scaled),
            0.0,
            1.0,
        ),
    )


def _phik_from_library(
    chi2: float,
    n: int,
    rows: int,
    cols: int,
    pedestal: int,
) -> float:
    try:
        return float(
            phik_from_chi2(
                chi2,
                n,
                nx=rows,
                ny=cols,
                pedestal=pedestal,
            ),
        )
    except (ValueError, ZeroDivisionError):
        return 0.0
