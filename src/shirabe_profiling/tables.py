"""Extra report tables: outliers and missing-value patterns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from shirabe_profiling.analyzers import NumericStats

if TYPE_CHECKING:
    from shirabe_profiling.analyzers import ColumnStats
    from shirabe_profiling.config import ProfileConfig

IQR_FENCE = 1.5
MAX_PATTERN_COLUMNS = 20
MAX_PATTERNS = 10


@dataclass(frozen=True)
class OutlierRow:
    """Outlier count for one numeric column, with the fences that were used."""

    column: str
    count: int
    pct: float
    lower: float
    upper: float


@dataclass(frozen=True)
class MissingPattern:
    """A group of columns that are empty in the same rows."""

    columns: list[str]
    rows: int
    pct: float


@dataclass(frozen=True)
class ReportTables:
    outliers: list[OutlierRow] = field(default_factory=list)
    missing_patterns: list[MissingPattern] = field(default_factory=list)
    complete_rows: int = 0
    patterns_truncated: bool = False


def compute_tables(
    df: pl.DataFrame,
    column_stats: dict[str, ColumnStats],
    config: ProfileConfig,
) -> ReportTables:
    """Compute the outlier and missing-pattern tables.

    Returns empty tables in overview mode or when the data has no rows.
    """
    if config.is_overview or df.height == 0:
        return ReportTables()

    patterns, complete_rows, truncated = _missing_patterns(
        df,
        column_stats,
    )
    return ReportTables(
        outliers=_outliers(
            df,
            column_stats,
        ),
        missing_patterns=patterns,
        complete_rows=complete_rows,
        patterns_truncated=truncated,
    )


def _outliers(
    df: pl.DataFrame,
    column_stats: dict[str, ColumnStats],
) -> list[OutlierRow]:
    fences: dict[str, tuple[float, float]] = {}
    for name, stats in column_stats.items():
        if not isinstance(stats, NumericStats):
            continue
        if stats.q25 is None or stats.q75 is None or not stats.iqr or stats.iqr <= 0:
            continue
        fences[name] = (stats.q25 - IQR_FENCE * stats.iqr, stats.q75 + IQR_FENCE * stats.iqr)

    if not fences:
        return []

    counts = df.select(
        ((pl.col(name) < lo) | (pl.col(name) > hi)).sum().alias(name)
        for name, (lo, hi) in fences.items()
    ).row(0, named=True)

    rows: list[OutlierRow] = []
    for name, (lo, hi) in fences.items():
        count = int(counts[name] or 0)
        stats = column_stats[name]
        non_null = stats.count - stats.missing_count
        if count > 0 and non_null > 0:
            rows.append(
                OutlierRow(
                    name,
                    count,
                    count / non_null,
                    lo,
                    hi,
                ),
            )

    rows.sort(
        key=lambda row: row.pct,
        reverse=True,
    )
    return rows


def _missing_patterns(
    df: pl.DataFrame,
    column_stats: dict[str, ColumnStats],
) -> tuple[list[MissingPattern], int, bool]:
    affected = sorted(
        (stats.missing_count, name)
        for name, stats in column_stats.items()
        if stats.missing_count > 0
    )
    if len(affected) < 2:
        return [], 0, False

    affected.reverse()
    truncated = len(affected) > MAX_PATTERN_COLUMNS
    names = [name for _, name in affected[:MAX_PATTERN_COLUMNS]]

    grouped = (
        df.select(pl.col(name).is_null().alias(name) for name in names)
        .group_by(names)
        .agg(pl.len().alias("_rows"))
        .sort("_rows", descending=True)
    )

    complete_rows = 0
    patterns: list[MissingPattern] = []
    for row in grouped.iter_rows(named=True):
        missing = [name for name in names if row[name]]
        rows = int(row["_rows"])
        if not missing:
            complete_rows = rows
        elif len(patterns) < MAX_PATTERNS:
            patterns.append(
                MissingPattern(
                    missing,
                    rows,
                    rows / df.height,
                ),
            )

    return patterns, complete_rows, truncated
