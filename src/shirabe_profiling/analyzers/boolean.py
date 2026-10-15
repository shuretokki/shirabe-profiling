from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from shirabe_profiling.analyzers import BooleanStats
from shirabe_profiling.type_inference import ColumnType

if TYPE_CHECKING:
    from shirabe_profiling.config import ProfileConfig


def analyze_boolean(
    df: pl.DataFrame,
    col_name: str,
    config: ProfileConfig,  # noqa: ARG001
) -> BooleanStats:
    col = pl.col(col_name)
    n_rows = df.height

    if n_rows == 0:
        return _empty_stats(col_name)

    row = df.select(
        col.null_count().alias("missing_count"),
        col.sum().alias("true_count"),
    ).row(0, named=True)

    missing_count: int = row["missing_count"]
    true_count: int = row["true_count"] or 0
    non_null = n_rows - missing_count
    false_count = non_null - true_count

    return BooleanStats(
        column_name=col_name,
        column_type=ColumnType.BOOLEAN,
        count=n_rows,
        missing_count=missing_count,
        missing_pct=missing_count / n_rows,
        true_count=true_count,
        true_pct=true_count / non_null if non_null > 0 else 0.0,
        false_count=false_count,
        false_pct=false_count / non_null if non_null > 0 else 0.0,
    )


def _empty_stats(col_name: str) -> BooleanStats:
    return BooleanStats(
        column_name=col_name,
        column_type=ColumnType.BOOLEAN,
        count=0,
        missing_count=0,
        missing_pct=0.0,
    )
