"""Skew transforms: how log1p and Yeo-Johnson change a skewed column."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
import polars as pl
from scipy.stats import skew, yeojohnson

from shirabe_profiling.alerts import AlertType
from shirabe_profiling.analyzers.numeric import analyze_numeric

if TYPE_CHECKING:
    from shirabe_profiling.alerts import Alert
    from shirabe_profiling.config import ProfileConfig

MAX_COLUMNS = 20
FIT_SAMPLE = 20_000

Variant = dict[str, Any]


def compute_skew_transforms(
    df: pl.DataFrame,
    alerts: list[Alert],
    config: ProfileConfig,
) -> list[dict[str, Any]]:
    """Compare the original values with log1p and Yeo-Johnson for each skewed column.

    The columns come from the Skewed alerts, most skewed first.
    Returns an empty list in overview mode or when the data has no rows.
    """
    if config.is_overview or df.height == 0:
        return []

    skewed = sorted(
        (
            alert
            for alert in alerts
            if alert.alert_type == AlertType.SKEWED
            and alert.column is not None
            and alert.column in df.columns
        ),
        key=lambda alert: abs(alert.value),
        reverse=True,
    )
    entries: list[dict[str, Any]] = []
    for alert in skewed[:MAX_COLUMNS]:
        column = cast(
            "str",
            alert.column,
        )
        entry = _entry(
            column,
            df[column],
            config,
        )
        if entry is not None:
            entries.append(entry)
    return entries


def _entry(
    column: str,
    series: pl.Series,
    config: ProfileConfig,
) -> dict[str, Any] | None:
    if not series.dtype.is_numeric():
        return None
    values = series.cast(
        pl.Float64,
        strict=False,
    ).to_numpy()
    observed = values[~np.isnan(values)]
    if observed.size < 3 or float(np.std(observed)) == 0.0:
        return None

    variants: dict[str, Variant | None] = {
        "original": _variant(values),
        "log1p": None,
        "yeojohnson": None,
        "nonzero": None,
    }
    if float(np.min(observed)) > -1:
        variants["log1p"] = _variant(
            np.log1p(values),
            column,
            config,
        )

    fitted = _yeo_johnson(
        values,
        observed,
        config.interaction_sample_seed,
    )
    if fitted is not None:
        after, power = fitted
        transformed = _variant(
            after,
            column,
            config,
        )
        transformed["power"] = f"{power:.2f}"
        variants["yeojohnson"] = transformed

    variants["nonzero"] = _non_zero(
        observed,
        column,
        config,
    )

    for key in ("log1p", "yeojohnson"):
        variant = variants[key]
        if variant is not None:
            variant["ok"] = abs(float(variant["skew_value"])) <= config.skewness_threshold

    return {
        "column": column,
        **variants,
    }


def _non_zero(
    observed: np.ndarray,
    column: str,
    config: ProfileConfig,
) -> Variant | None:
    """Apply log1p to the values that are not zero, for a column with many zeros.

    No transform can spread a spike of zeros, so the zeros are set aside.
    This variant uses fewer rows, so it carries no `ok` mark.
    """
    zero_share = float(np.mean(observed == 0))
    kept = observed[observed != 0]
    if zero_share < config.zero_threshold or kept.size < 3 or float(np.min(kept)) <= -1:
        return None
    shrunk = np.log1p(kept)
    if float(np.std(shrunk)) == 0.0:
        return None
    variant = _variant(
        shrunk,
        column,
        config,
    )
    variant["zeros"] = f"{zero_share:.0%}"
    return variant


def _yeo_johnson(
    values: np.ndarray,
    observed: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, float] | None:
    """Fit the power on a sample, then apply it to every value."""
    sample = observed
    if observed.size > FIT_SAMPLE:
        sample = np.random.default_rng(seed).choice(
            observed,
            size=FIT_SAMPLE,
            replace=False,
        )
    try:
        _, power = cast(
            "tuple[np.ndarray, float]",
            yeojohnson(sample),
        )
        transformed = cast(
            "np.ndarray",
            yeojohnson(
                observed,
                lmbda=power,
            ),
        )
    except (ValueError, FloatingPointError, OverflowError):
        return None
    if not np.all(np.isfinite(transformed)):
        return None
    after = values.copy()
    after[~np.isnan(values)] = transformed
    return after, float(power)


def _variant(
    values: np.ndarray,
    column: str | None = None,
    config: ProfileConfig | None = None,
) -> Variant:
    """Summarize one version of a column.

    With a column name and a config, it also holds the full numeric statistics.
    """
    observed = values[~np.isnan(values)]
    skew_value = float(
        cast(
            "float",
            skew(observed),
        ),
    )
    variant: Variant = {
        "skew": _num(skew_value),
        "skew_value": skew_value,
    }
    if column is not None and config is not None:
        variant["numeric"] = analyze_numeric(
            pl.DataFrame({column: pl.Series(values).fill_nan(None)}),
            column,
            config,
        )
    return variant


def _num(value: float) -> str:
    if not np.isfinite(value):
        return "n/a"
    magnitude = abs(value)
    if magnitude >= 1000:
        return f"{value:,.0f}"
    if magnitude >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"
