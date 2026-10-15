from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import polars as pl

from shirabe_profiling.analyzers import DatetimeStats
from shirabe_profiling.type_inference import ColumnType

if TYPE_CHECKING:
    from datetime import datetime

    from shirabe_profiling.config import ProfileConfig

MAX_TIMELINE_BARS = 60
_TIMELINE_UNITS = (
    ("hour", "1h", 3_600.0, "%Y-%m-%d %H:00"),
    ("day", "1d", 86_400.0, "%Y-%m-%d"),
    ("month", "1mo", 2_629_800.0, "%Y-%m"),
    ("year", "1y", 31_557_600.0, "%Y"),
)


def analyze_datetime(
    df: pl.DataFrame,
    col_name: str,
    config: ProfileConfig,  # noqa: ARG001
) -> DatetimeStats:
    col = pl.col(col_name)
    n_rows = df.height

    if n_rows == 0:
        return _empty_stats(col_name)

    row = df.select(
        col.null_count().alias("missing_count"),
        col.drop_nulls().n_unique().alias("distinct_count"),
        col.min().alias("min"),
        col.max().alias("max"),
    ).row(0, named=True)

    missing_count: int = row["missing_count"]
    distinct_count: int = row["distinct_count"]
    min_val = row["min"]
    max_val = row["max"]

    range_str = _compute_range(
        min_val,
        max_val,
    )
    unit, timeline = _timeline(
        df[col_name],
        min_val,
        max_val,
    )

    return DatetimeStats(
        column_name=col_name,
        column_type=ColumnType.DATETIME,
        count=n_rows,
        missing_count=missing_count,
        missing_pct=missing_count / n_rows,
        distinct_count=distinct_count,
        distinct_pct=distinct_count / n_rows,
        min=str(min_val) if min_val is not None else None,
        max=str(max_val) if max_val is not None else None,
        range=range_str,
        timeline_unit=unit,
        timeline=timeline,
    )


def _timeline(
    series: pl.Series,
    min_val: Any,
    max_val: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Count the rows per period, with the period sized to give at most 60 bars."""
    if min_val is None or max_val is None or not isinstance(series.dtype, pl.Date | pl.Datetime):
        return "", []
    try:
        span = (max_val - min_val).total_seconds()
    except (TypeError, AttributeError):
        return "", []
    options = _TIMELINE_UNITS if span >= _TIMELINE_UNITS[0][2] else _TIMELINE_UNITS[1:]
    unit, every, _, pattern = next(
        (option for option in options if span / option[2] <= MAX_TIMELINE_BARS),
        _TIMELINE_UNITS[-1],
    )
    values = series.drop_nulls()
    if isinstance(values.dtype, pl.Date):
        values = values.cast(pl.Datetime)
    starts = values.dt.truncate(every)
    counts = starts.value_counts()
    counts = counts.rename({counts.columns[0]: "start"})
    try:
        grid = pl.DataFrame(
            {
                "start": pl.datetime_range(
                    cast(
                        "datetime",
                        starts.min(),
                    ),
                    cast(
                        "datetime",
                        starts.max(),
                    ),
                    interval=every,
                    time_unit=cast(
                        "Any",
                        starts.dtype,
                    ).time_unit,
                    time_zone=cast(
                        "Any",
                        starts.dtype,
                    ).time_zone,
                    eager=True,
                ),
            },
        )
        counts = grid.join(
            counts,
            on="start",
            how="left",
        ).with_columns(pl.col("count").fill_null(0))
    except pl.exceptions.PolarsError:
        pass
    counts = counts.sort("start")
    labels = counts["start"].dt.strftime(pattern).to_list()
    return unit, [
        {
            "label": label,
            "count": int(count),
        }
        for label, count in zip(
            labels,
            counts["count"].to_list(),
            strict=True,
        )
    ]


def _compute_range(
    min_val: Any,
    max_val: Any,
) -> str | None:
    if min_val is None or max_val is None:
        return None
    try:
        delta = max_val - min_val
        return str(delta)
    except TypeError:
        return None


def _empty_stats(col_name: str) -> DatetimeStats:
    return DatetimeStats(
        column_name=col_name,
        column_type=ColumnType.DATETIME,
        count=0,
        missing_count=0,
        missing_pct=0.0,
    )
