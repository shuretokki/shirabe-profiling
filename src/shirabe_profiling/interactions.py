# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Interaction data for scatter and box plots — Polars-native.

Scatter: numeric × numeric raw data (columnar).
Box plot: categorical × numeric five-number summary + outliers via IQR × 1.5.

Sampling at config.interaction_sample_size threshold; seed for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from shirabe_profiling.type_inference import ColumnType

if TYPE_CHECKING:
    from shirabe_profiling.config import ProfileConfig

_BOXPLOT_BATCH = 8
_NUM = "__column__"
_VALUE = "__value__"


@dataclass(
    frozen=True,
    slots=True,
)
class BoxPlotGroup:
    """Five-number summary + outliers for one category."""

    category: str
    min: float
    q1: float
    median: float
    q3: float
    max: float
    outliers: list[float] = field(default_factory=list)


@dataclass(
    frozen=True,
    slots=True,
)
class InteractionData:
    """Pre-computed data for the Interactions report section."""

    numeric_columns: list[str]
    categorical_columns: list[str]
    numeric_data: dict[str, list[float]]
    boxplot_stats: dict[str, dict[str, list[BoxPlotGroup]]]
    sampled: bool
    total_rows: int
    sample_size: int


def compute_interactions(
    df: pl.DataFrame,
    column_types: dict[str, ColumnType],
    config: ProfileConfig | None = None,
) -> InteractionData | None:
    """Compute interaction data for scatter and box plots.

    Returns None when there is nothing useful to show (overview mode,
    too few rows, or insufficient column variety).
    """
    if config is not None and config.is_overview:
        return None

    if df.height < 2:
        return None

    numeric_cols = _filter_numeric(
        df,
        column_types,
    )
    categorical_cols = _filter_categorical(
        df,
        column_types,
        config,
    )

    has_scatter = len(numeric_cols) >= 2
    has_boxplot = len(numeric_cols) >= 1 and len(categorical_cols) >= 1

    if not has_scatter and not has_boxplot:
        return None

    total_rows = df.height
    sample_limit = config.interaction_sample_size if config else 100_000

    sampled = total_rows > sample_limit
    if sampled:
        seed = config.interaction_sample_seed if config else 42
        df_work = df.sample(
            n=sample_limit,
            seed=seed,
        )
    else:
        df_work = df

    numeric_data = _extract_numeric_data(
        df_work,
        numeric_cols,
    )
    boxplot_stats = _compute_boxplot_stats(
        df_work,
        categorical_cols,
        numeric_cols,
    )

    return InteractionData(
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        numeric_data=numeric_data,
        boxplot_stats=boxplot_stats,
        sampled=sampled,
        total_rows=total_rows,
        sample_size=df_work.height,
    )


# -- Column filtering --------------------------------------------------------


def _filter_numeric(
    df: pl.DataFrame,
    column_types: dict[str, ColumnType],
) -> list[str]:
    """Keep numeric columns that are non-constant and have enough non-null values."""
    result: list[str] = []
    for col, ct in sorted(column_types.items()):
        if ct is not ColumnType.NUMERIC:
            continue
        series = df[col].drop_nulls()
        if series.len() < 2 or series.n_unique() < 2:
            continue
        result.append(col)
    return result


def _filter_categorical(
    df: pl.DataFrame,
    column_types: dict[str, ColumnType],
    config: ProfileConfig | None,
) -> list[str]:
    """Keep categorical columns under the cardinality limit."""
    limit = config.interaction_cardinality_limit if config else 50
    result: list[str] = []
    for col, ct in sorted(column_types.items()):
        if ct is not ColumnType.CATEGORICAL:
            continue
        if df[col].drop_nulls().n_unique() > limit:
            continue
        result.append(col)
    return result


# -- Numeric data extraction --------------------------------------------------


def _extract_numeric_data(
    df: pl.DataFrame,
    numeric_cols: list[str],
) -> dict[str, list[float]]:
    """Extract numeric column values as lists, rounded to 4 decimals."""
    data: dict[str, list[float]] = {}
    for col in numeric_cols:
        values = df[col].drop_nulls().cast(pl.Float64)
        data[col] = [round(v, 4) for v in values.to_list()]
    return data


# -- Box plot computation -----------------------------------------------------


def _compute_boxplot_stats(
    df: pl.DataFrame,
    categorical_cols: list[str],
    numeric_cols: list[str],
) -> dict[str, dict[str, list[BoxPlotGroup]]]:
    """Compute five-number summary + outliers for each categorical × numeric pair."""
    if not categorical_cols or not numeric_cols:
        return {}

    stats: dict[str, dict[str, list[BoxPlotGroup]]] = {}
    for cat_col in categorical_cols:
        found: dict[str, list[BoxPlotGroup]] = {}
        for start in range(0, len(numeric_cols), _BOXPLOT_BATCH):
            batch = numeric_cols[start : start + _BOXPLOT_BATCH]
            found.update(
                _boxplot_for_batch(
                    df,
                    cat_col,
                    batch,
                ),
            )
        stats[cat_col] = {col: found[col] for col in numeric_cols if col in found}

    return stats


def boxplot_for_pair(
    df: pl.DataFrame,
    cat_col: str,
    num_col: str,
) -> list[BoxPlotGroup]:
    """Compute BoxPlotGroup for each category in cat_col vs num_col."""
    return _boxplot_for_batch(
        df,
        cat_col,
        [num_col],
    ).get(num_col, [])


def _boxplot_for_batch(
    df: pl.DataFrame,
    cat_col: str,
    num_cols: list[str],
) -> dict[str, list[BoxPlotGroup]]:
    """Compute BoxPlotGroup for each category of cat_col against several numeric columns."""
    long = (
        df.select(
            pl.col(cat_col),
            *(pl.col(c).cast(pl.Float64) for c in num_cols),
        )
        .unpivot(num_cols, index=cat_col, variable_name=_NUM, value_name=_VALUE)
        .drop_nulls()
    )
    if long.is_empty():
        return {}

    value = pl.col(_VALUE)
    keys = [cat_col, _NUM]
    summary = (
        long.group_by(keys)
        .agg(
            value.min().alias("min"),
            value.quantile(0.25).alias("q1"),
            value.quantile(0.5).alias("median"),
            value.quantile(0.75).alias("q3"),
            value.max().alias("max"),
        )
        .with_columns(
            (pl.col("q1") - 1.5 * (pl.col("q3") - pl.col("q1"))).alias("lower"),
            (pl.col("q3") + 1.5 * (pl.col("q3") - pl.col("q1"))).alias("upper"),
        )
        .sort(keys)
    )
    outliers = (
        long.join(
            summary.select(
                *keys,
                "lower",
                "upper",
            ),
            on=keys,
        )
        .filter((value < pl.col("lower")) | (value > pl.col("upper")))
        .group_by(keys)
        .agg(value.alias("outliers"))
    )
    rows = summary.join(
        outliers,
        on=keys,
        how="left",
    )

    result: dict[str, list[BoxPlotGroup]] = {}
    for row in rows.iter_rows(named=True):
        found = row["outliers"] or []
        result.setdefault(
            row[_NUM],
            [],
        ).append(
            BoxPlotGroup(
                category=str(row[cat_col]),
                min=round(max(row["min"], row["lower"]), 2),
                q1=round(row["q1"], 2),
                median=round(row["median"], 2),
                q3=round(row["q3"], 2),
                max=round(min(row["max"], row["upper"]), 2),
                outliers=[round(v, 2) for v in found],
            ),
        )
    return result
