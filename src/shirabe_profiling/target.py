"""Target analysis: how each column relates to the column that a model will predict."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import numpy as np
import polars as pl

from shirabe_profiling.alerts import Alert, AlertType
from shirabe_profiling.correlations import (
    Coded,
    bin_numeric,
    encode_categories,
    numeric_matrix,
    pairwise_pearson,
    phik_value,
    rank_columns,
)
from shirabe_profiling.type_inference import ColumnType

if TYPE_CHECKING:
    from shirabe_profiling.config import ProfileConfig

CLASS_LIMIT = 10
MAX_LEVELS = 12
MAX_BINS = 10
MAX_FEATURE_LEVELS = 50
MIN_GROUP_ROWS = 5
MAX_MISSING_LINKS = 10
POSITIVE_LABELS = ("1", "true", "yes", "y", "t")
_FEATURE_TYPES = (ColumnType.NUMERIC, ColumnType.CATEGORICAL, ColumnType.BOOLEAN)


@dataclass(frozen=True)
class TargetClass:
    label: str
    count: int
    share: float


@dataclass(frozen=True)
class TargetSummary:
    """The target column: its task, its size, and the number that the breakdowns compare to."""

    column: str
    task: Literal["classification", "regression"]
    rows: int
    missing: int
    value_label: str
    overall: float
    focus: str | None = None
    classes: list[TargetClass] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)
    log_skew: float | None = None


@dataclass(frozen=True)
class FeatureLink:
    """The strength of the link between one column and the target."""

    column: str
    kind: Literal["numeric", "category"]
    association: float
    direction: float | None = None


@dataclass(frozen=True)
class BreakdownBin:
    label: str
    count: int
    value: float


@dataclass(frozen=True)
class FeatureBreakdown:
    column: str
    association: float
    bins: list[BreakdownBin]


@dataclass(frozen=True)
class MissingLink:
    """The target value in rows where a column is missing, against the other rows."""

    column: str
    missing_rows: int
    missing_value: float
    present_value: float
    gap: float


@dataclass(frozen=True)
class TargetAnalysis:
    summary: TargetSummary
    links: list[FeatureLink] = field(default_factory=list)
    breakdowns: list[FeatureBreakdown] = field(default_factory=list)
    missing_links: list[MissingLink] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def compute_target(
    df: pl.DataFrame,
    column_types: dict[str, ColumnType],
    config: ProfileConfig,
) -> TargetAnalysis | None:
    """Relate every column to the target. Returns None when no target is set."""
    name = config.target
    if name is None:
        return None
    if name not in df.columns:
        shown = ", ".join(df.columns[:10]) + (", ..." if df.width > 10 else "")
        msg = f"target '{name}' is not a column of the data. Columns: {shown}"
        raise ValueError(msg)

    task = _task(
        df[name],
        column_types[name],
        name,
    )
    work = _rows_with_target(
        df,
        name,
        task,
    )
    if work.height == 0:
        msg = f"target '{name}' has no values"
        raise ValueError(msg)

    labels = work[name].cast(pl.String) if task == "classification" else None
    summary, y = _summarize(
        name,
        work,
        labels,
        df.height - work.height,
    )

    features = [
        col for col, kind in column_types.items() if col != name and kind in _FEATURE_TYPES
    ]
    kept, skipped = _split_by_levels(
        work,
        features,
        column_types,
    )
    target_coded = encode_categories(labels) if labels is not None else bin_numeric(y)
    links = _links(
        work,
        kept,
        column_types,
        target_coded,
        name,
        column_types[name],
    )

    ranked = [link for link in links if link.association > 0]
    breakdowns = [
        FeatureBreakdown(
            link.column,
            link.association,
            _breakdown(
                work,
                y,
                link.column,
                column_types[link.column],
            ),
        )
        for link in ranked[: config.target_max_features]
    ]
    return TargetAnalysis(
        summary=summary,
        links=links,
        breakdowns=breakdowns,
        missing_links=_missing_links(
            work,
            y,
            kept,
            task,
        ),
        skipped=skipped,
    )


def target_alerts(
    analysis: TargetAnalysis,
    config: ProfileConfig,
) -> list[Alert]:
    """Flag columns that link so closely to the target that they may leak it."""
    return [
        Alert(
            link.column,
            AlertType.TARGET_LEAKAGE,
            link.association,
            {"target": analysis.summary.column},
        )
        for link in analysis.links
        if link.association >= config.leakage_threshold
    ]


# -- Target summary --------------------------------------------------------


def _task(
    series: pl.Series,
    kind: ColumnType,
    name: str,
) -> Literal["classification", "regression"]:
    if kind in (ColumnType.CATEGORICAL, ColumnType.BOOLEAN):
        return "classification"
    if kind is ColumnType.NUMERIC:
        values = series.drop_nulls()
        if values.dtype.is_integer() and values.n_unique() <= CLASS_LIMIT:
            return "classification"
        return "regression"
    msg = f"target '{name}' has type {kind.name}. Use a numeric, boolean or category column."
    raise ValueError(msg)


def _rows_with_target(
    df: pl.DataFrame,
    name: str,
    task: str,
) -> pl.DataFrame:
    if task == "classification":
        return df.filter(pl.col(name).is_not_null())
    return df.filter(pl.col(name).cast(pl.Float64).is_finite())


def _summarize(
    name: str,
    work: pl.DataFrame,
    labels: pl.Series | None,
    missing: int,
) -> tuple[TargetSummary, np.ndarray]:
    if labels is not None:
        counts = labels.value_counts(sort=True).sort(
            ["count", labels.name],
            descending=[True, False],
        )
        classes = [
            TargetClass(
                str(row[labels.name]),
                int(row["count"]),
                row["count"] / work.height,
            )
            for row in counts.iter_rows(named=True)
        ]
        focus = _focus(classes)
        y = (labels == focus).cast(pl.Float64).to_numpy()
        summary = TargetSummary(
            column=name,
            task="classification",
            rows=work.height,
            missing=missing,
            value_label=f"Share with {name} = {focus}",
            overall=float(y.mean()),
            focus=focus,
            classes=classes[:CLASS_LIMIT],
        )
        return summary, y

    y = work[name].cast(pl.Float64).to_numpy()
    series = pl.Series(y)
    log_skew = None
    std = series.std()
    if y.min() >= 0:
        log_skew = _skew(pl.Series(np.log1p(y)))
    stats = {
        "mean": float(y.mean()),
        "median": float(np.median(y)),
        "std": float(std) if isinstance(std, (int, float)) else 0.0,
        "min": float(y.min()),
        "max": float(y.max()),
    }
    skew = _skew(series)
    if skew is not None:
        stats["skew"] = skew
    summary = TargetSummary(
        column=name,
        task="regression",
        rows=work.height,
        missing=missing,
        value_label=f"Mean of {name}",
        overall=stats["mean"],
        stats=stats,
        log_skew=log_skew,
    )
    return summary, y


def _skew(series: pl.Series) -> float | None:
    value = series.skew()
    return float(value) if value is not None and np.isfinite(value) else None


def _focus(classes: list[TargetClass]) -> str:
    """Pick the class that the breakdowns follow."""
    if len(classes) == 2:
        by_name = {item.label.lower(): item.label for item in classes}
        for key in POSITIVE_LABELS:
            if key in by_name:
                return by_name[key]
        return min(classes, key=lambda item: item.count).label
    return classes[0].label


# -- Links to the target ---------------------------------------------------


def _split_by_levels(
    work: pl.DataFrame,
    features: list[str],
    column_types: dict[str, ColumnType],
) -> tuple[list[str], list[str]]:
    """Set aside category columns with so many levels that any link would be by chance."""
    kept: list[str] = []
    skipped: list[str] = []
    for name in features:
        too_many = (
            column_types[name] is not ColumnType.NUMERIC
            and work[name].n_unique() > MAX_FEATURE_LEVELS
        )
        (skipped if too_many else kept).append(name)
    return kept, skipped


def _links(
    work: pl.DataFrame,
    features: list[str],
    column_types: dict[str, ColumnType],
    target_coded: Coded,
    target: str,
    target_kind: ColumnType,
) -> list[FeatureLink]:
    numeric_target = target_kind is ColumnType.NUMERIC
    directions = (
        _directions(
            work,
            features,
            column_types,
            target,
        )
        if numeric_target
        else {}
    )
    links: list[FeatureLink] = []
    for name in features:
        numeric = column_types[name] is ColumnType.NUMERIC
        coded = (
            bin_numeric(
                numeric_matrix(
                    work,
                    [name],
                )[:, 0],
            )
            if numeric
            else encode_categories(work[name])
        )
        strength = phik_value(
            coded,
            target_coded,
        )
        links.append(
            FeatureLink(
                column=name,
                kind="numeric" if numeric else "category",
                association=float(strength) if np.isfinite(strength) else 0.0,
                direction=directions.get(name),
            ),
        )
    links.sort(key=lambda link: (-link.association, link.column))
    return links


def _directions(
    work: pl.DataFrame,
    features: list[str],
    column_types: dict[str, ColumnType],
    target: str,
) -> dict[str, float]:
    """Spearman correlation with a numeric target, for the numeric columns."""
    numeric = [name for name in features if column_types[name] is ColumnType.NUMERIC]
    if not numeric:
        return {}
    ranked = rank_columns(
        numeric_matrix(
            work,
            [target, *numeric],
        ),
    )
    estimates, _ = pairwise_pearson(ranked)
    return {
        name: float(estimates[0, index + 1])
        for index, name in enumerate(numeric)
        if np.isfinite(estimates[0, index + 1])
    }


# -- Breakdown by value ----------------------------------------------------


def _breakdown(
    work: pl.DataFrame,
    y: np.ndarray,
    name: str,
    kind: ColumnType,
) -> list[BreakdownBin]:
    if kind is ColumnType.NUMERIC:
        return _numeric_breakdown(
            numeric_matrix(
                work,
                [name],
            )[:, 0],
            y,
        )
    return _category_breakdown(
        work[name].cast(pl.String),
        y,
    )


def _numeric_breakdown(
    values: np.ndarray,
    y: np.ndarray,
) -> list[BreakdownBin]:
    keep = np.isfinite(values)
    values, y = values[keep], y[keep]
    if values.size == 0:
        return []

    distinct = np.unique(values)
    if len(distinct) <= MAX_LEVELS:
        codes = np.searchsorted(
            distinct,
            values,
        )
        labels = [_number(item) for item in distinct]
    else:
        edges = np.unique(
            np.quantile(
                values,
                np.linspace(
                    0.0,
                    1.0,
                    MAX_BINS + 1,
                ),
            ),
        )
        codes = np.digitize(
            values,
            edges[1:-1],
            right=True,
        )
        labels = [f"{_number(edges[i])} to {_number(edges[i + 1])}" for i in range(len(edges) - 1)]

    counts = np.bincount(
        codes,
        minlength=len(labels),
    )
    totals = np.bincount(
        codes,
        weights=y,
        minlength=len(labels),
    )
    return [
        BreakdownBin(
            labels[i],
            int(counts[i]),
            float(totals[i] / counts[i]),
        )
        for i in range(len(labels))
        if counts[i] > 0
    ]


def _category_breakdown(
    series: pl.Series,
    y: np.ndarray,
) -> list[BreakdownBin]:
    grouped = (
        pl.DataFrame({"level": series, "y": y})
        .drop_nulls("level")
        .group_by("level")
        .agg(pl.len().alias("n"), pl.col("y").sum().alias("total"))
        .sort(["n", "level"], descending=[True, False])
    )
    rows = grouped.rows()
    if len(rows) > MAX_LEVELS:
        rest = rows[MAX_LEVELS - 1 :]
        merged = ("Other", sum(r[1] for r in rest), sum(r[2] for r in rest))
        rows = [*rows[: MAX_LEVELS - 1], merged]
    return [
        BreakdownBin(
            str(level),
            int(n),
            float(total / n),
        )
        for level, n, total in rows
    ]


def _number(value: float) -> str:
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.4g}"


# -- Missing values and the target -----------------------------------------


def _missing_links(
    work: pl.DataFrame,
    y: np.ndarray,
    features: list[str],
    task: str,
) -> list[MissingLink]:
    spread = float(y.std()) if task == "regression" else 1.0
    spread = spread if spread > 0 else 1.0

    found: list[tuple[float, MissingLink]] = []
    for name in features:
        gone = work[name].is_null()
        if work[name].dtype.is_float():
            gone = gone | work[name].is_nan()
        mask = gone.to_numpy()
        missing = int(mask.sum())
        if missing < MIN_GROUP_ROWS or len(mask) - missing < MIN_GROUP_ROWS:
            continue
        with_gap = float(y[mask].mean())
        without_gap = float(y[~mask].mean())
        gap = with_gap - without_gap
        found.append(
            (
                abs(gap) / spread,
                MissingLink(
                    name,
                    missing,
                    with_gap,
                    without_gap,
                    gap,
                ),
            ),
        )

    found.sort(key=lambda item: (-item[0], item[1].column))
    return [link for _, link in found[:MAX_MISSING_LINKS]]
