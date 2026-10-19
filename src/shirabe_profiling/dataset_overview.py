# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl

from shirabe_profiling.type_inference import ColumnType  # noqa: TC001 — used at runtime

if TYPE_CHECKING:
    from shirabe_profiling.config import ProfileConfig

_SAMPLE_SIZE = 10


@dataclass(frozen=True)
class DatasetOverview:
    n_rows: int
    n_columns: int
    missing_cells: int
    missing_cells_pct: float
    duplicate_rows: int
    duplicate_rows_pct: float
    memory_bytes: int
    memory_human: str
    type_distribution: dict[str, int] = field(default_factory=dict)
    missing_per_column: dict[str, dict[str, Any]] = field(default_factory=dict)
    sample_head: list[dict[str, Any]] = field(default_factory=list)
    sample_tail: list[dict[str, Any]] = field(default_factory=list)
    duplicate_rows_sample: list[dict[str, Any]] = field(default_factory=list)
    sample_random: list[dict[str, Any]] = field(default_factory=list)
    sample_most_missing: list[dict[str, Any]] = field(default_factory=list)
    rows_with_missing: int = 0
    reproduction: dict[str, str] = field(default_factory=dict)


def compute_overview(
    df: pl.DataFrame,
    column_types: dict[str, ColumnType],
    config: ProfileConfig | None = None,
) -> DatasetOverview:
    from shirabe_profiling.config import ProfileConfig as _PC

    config = config or _PC()
    n_rows = df.height
    n_columns = df.width
    total_cells = n_rows * n_columns

    missing_cells = _total_missing(df)
    duplicate_rows = _duplicate_count(
        df,
        n_rows,
    )
    memory_bytes = int(df.estimated_size())

    type_dist: dict[str, int] = {}
    for ct in column_types.values():
        type_dist[ct.name] = (
            type_dist.get(
                ct.name,
                0,
            )
            + 1
        )

    missing_per_col = _missing_per_column(
        df,
        n_rows,
    )
    sample_head = _sample_rows(df.head(_SAMPLE_SIZE))
    sample_tail = _sample_rows(df.tail(_SAMPLE_SIZE))

    dup_sample: list[dict[str, Any]] = []
    if not config.is_overview and duplicate_rows > 0:
        dup_sample = _duplicate_rows_sample(df)

    random_sample: list[dict[str, Any]] = []
    most_missing: list[dict[str, Any]] = []
    rows_with_missing = 0
    if not config.is_overview:
        random_sample = _random_rows(
            df,
            config.interaction_sample_seed,
        )
        most_missing, rows_with_missing = _most_missing_rows(df)

    reproduction = _reproduction_info(config)

    return DatasetOverview(
        n_rows=n_rows,
        n_columns=n_columns,
        missing_cells=missing_cells,
        missing_cells_pct=missing_cells / total_cells if total_cells > 0 else 0.0,
        duplicate_rows=duplicate_rows,
        duplicate_rows_pct=duplicate_rows / n_rows if n_rows > 0 else 0.0,
        memory_bytes=memory_bytes,
        memory_human=_format_bytes(memory_bytes),
        type_distribution=type_dist,
        missing_per_column=missing_per_col,
        sample_head=sample_head,
        sample_tail=sample_tail,
        duplicate_rows_sample=dup_sample,
        sample_random=random_sample,
        sample_most_missing=most_missing,
        rows_with_missing=rows_with_missing,
        reproduction=reproduction,
    )


def _total_missing(df: pl.DataFrame) -> int:
    if df.height == 0 or df.width == 0:
        return 0
    return sum(df.select(pl.all().null_count()).row(0))


def _missing_per_column(
    df: pl.DataFrame,
    n_rows: int,
) -> dict[str, dict[str, Any]]:
    if df.height == 0 or df.width == 0:
        return {}
    null_counts = df.select(pl.all().null_count()).row(
        0,
        named=True,
    )
    result: dict[str, dict[str, Any]] = {}
    for col_name, null_count in null_counts.items():
        result[col_name] = {
            "count": null_count,
            "pct": null_count / n_rows if n_rows > 0 else 0.0,
        }
    return result


def _duplicate_count(
    df: pl.DataFrame,
    n_rows: int,
) -> int:
    if n_rows == 0:
        return 0
    n_unique = df.select(pl.struct(pl.all()).n_unique()).item()
    return n_rows - n_unique


def _duplicate_rows_sample(
    df: pl.DataFrame,
    max_rows: int = _SAMPLE_SIZE,
) -> list[dict[str, Any]]:
    try:
        dupes = df.filter(df.is_duplicated()).head(max_rows)
        return _sample_rows(dupes)
    except Exception:
        return []


def _random_rows(
    df: pl.DataFrame,
    seed: int,
    max_rows: int = _SAMPLE_SIZE,
) -> list[dict[str, Any]]:
    """Draw a seeded random set of rows, in their original order.

    Returns nothing when the head and the tail already cover the data.
    """
    if df.height <= 2 * max_rows:
        return []
    drawn = (
        df.with_row_index("__row")
        .sample(
            n=max_rows,
            seed=seed,
        )
        .sort("__row")
        .drop("__row")
    )
    return _sample_rows(drawn)


def _most_missing_rows(
    df: pl.DataFrame,
    max_rows: int = _SAMPLE_SIZE,
) -> tuple[list[dict[str, Any]], int]:
    """Return the rows with the most missing values and the count of rows with any."""
    if df.height == 0 or df.width == 0:
        return [], 0
    counts = df.select(pl.sum_horizontal(pl.all().is_null())).to_series()
    with_missing = int((counts > 0).sum())
    if with_missing == 0:
        return [], 0
    worst = (
        df.with_columns(counts.alias("__missing"))
        .with_row_index("__row")
        .filter(pl.col("__missing") > 0)
        .sort(
            ["__missing", "__row"],
            descending=[True, False],
        )
        .head(max_rows)
        .drop(["__missing", "__row"])
    )
    return _sample_rows(worst), with_missing


def _sample_rows(df: pl.DataFrame) -> list[dict[str, Any]]:
    if df.height == 0:
        return []
    return [
        {col: str(val) if val is not None else None for col, val in row.items()}
        for row in df.iter_rows(named=True)
    ]


def _reproduction_info(config: ProfileConfig) -> dict[str, str]:
    import platform

    import shirabe_profiling

    info = {
        "shirabe_profiling_version": shirabe_profiling.__version__,
        "polars_version": pl.__version__,
        "python_version": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": config.mode,
    }
    for package in ("polars-statistics", "scipy", "phik"):
        version = _package_version(package)
        if version is not None:
            info[f"{package.replace('-', '_')}_version"] = version

    settings = {
        "alert.missing_threshold": config.missing_threshold,
        "alert.cardinality_threshold": config.cardinality_threshold,
        "alert.correlation_threshold": config.correlation_threshold,
        "alert.constant_threshold": config.constant_threshold,
        "alert.zero_threshold": config.zero_threshold,
        "alert.infinite_threshold": config.infinite_threshold,
        "alert.skewness_threshold": config.skewness_threshold,
        "alert.imbalance_threshold": config.imbalance_threshold,
        "alert.duplicate_threshold": config.duplicate_threshold,
        "alert.uniform_pvalue_threshold": config.uniform_pvalue_threshold,
        "type.text_unique_ratio": config.text_unique_ratio,
        "interactions.sample_size": config.interaction_sample_size,
        "interactions.sample_seed": config.interaction_sample_seed,
        "interactions.cardinality_limit": config.interaction_cardinality_limit,
        "correlations.kendall_max_columns": config.kendall_max_columns,
        "correlations.heatmap_max_columns": config.correlation_heatmap_max_columns,
        "correlations.heatmap_max_columns_mobile": config.correlation_heatmap_max_columns_mobile,
        "target.column": config.target or "none",
        "target.max_features": config.target_max_features,
        "alert.leakage_threshold": config.leakage_threshold,
        "display.n_top_values": config.n_top_values,
        "display.histogram_bins": config.histogram_bins,
    }
    info.update({key: str(value) for key, value in settings.items()})
    if config.column_overrides:
        info["column_overrides"] = ", ".join(sorted(config.column_overrides))
    return info


def _package_version(package: str) -> str | None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"
