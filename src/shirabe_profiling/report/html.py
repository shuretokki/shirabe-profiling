"""HTML report rendering via Jinja2."""

from __future__ import annotations

import base64
import json
import math
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

from jinja2 import Environment, FileSystemLoader

from shirabe_profiling.alerts import Alert  # noqa: TC001 — used at runtime
from shirabe_profiling.analyzers import (
    BooleanStats,
    CategoricalStats,
    ColumnStats,
    DatetimeStats,
    NumericStats,
)
from shirabe_profiling.correlations import CorrelationResult  # noqa: TC001
from shirabe_profiling.dataset_overview import DatasetOverview  # noqa: TC001 — used at runtime
from shirabe_profiling.interactions import InteractionData  # noqa: TC001
from shirabe_profiling.report.charts import ChartRenderer, EChartsRenderer
from shirabe_profiling.reproduction import describe_call
from shirabe_profiling.tables import ReportTables
from shirabe_profiling.target import TargetAnalysis  # noqa: TC001

if TYPE_CHECKING:
    from shirabe_profiling.config import ProfileConfig

_TEMPLATE_DIR = Path(__file__).parent / "templates"

PACKAGE_NAME = "shirabe-profiling"
BRAND_NAME = "shirabe"
REPOSITORY_URL = "https://github.com/shuretokki/shirabe-profiling"


_FONTS = (
    ("IBM Plex Sans", 400, "IBMPlexSans-Regular.woff"),
    ("IBM Plex Sans", 600, "IBMPlexSans-SemiBold.woff"),
    ("Lilex", 400, "Lilex-Regular.woff"),
)


def render_html(
    *,
    title: str,
    version: str,
    overview: DatasetOverview,
    column_stats: dict[str, ColumnStats],
    alerts: list[Alert],
    correlations: dict[str, CorrelationResult],
    interactions: InteractionData | None = None,
    tables: ReportTables | None = None,
    target: TargetAnalysis | None = None,
    config: ProfileConfig | None = None,
    reproduction_code: str | None = None,
    skew: list[dict[str, Any]] | None = None,
    chart_renderer: ChartRenderer | None = None,
) -> str:
    renderer = chart_renderer or EChartsRenderer()
    env = _build_env()
    template = env.get_template("report.html.j2")

    columns = _prepare_columns(
        column_stats,
        renderer,
        skew,
        alerts,
        config.skewness_threshold if config else 2.0,
    )
    heatmap_limit = config.correlation_heatmap_max_columns if config else 100
    mobile_limit = config.correlation_heatmap_max_columns_mobile if config else 20
    correlation_charts = _prepare_correlation_charts(
        correlations,
        renderer,
        heatmap_limit,
        mobile_limit,
    )
    interactions_payload = _prepare_interactions(interactions)
    alert_dicts = [
        {
            "column": a.column,
            "alert_type": a.alert_type.name,
            "value": a.value,
            "details": a.details,
        }
        for a in alerts
    ]

    ov_dict = asdict(overview)
    code = reproduction_code or describe_call(
        None,
        title=title,
        config=config,
    )

    return template.render(
        title=title,
        version=version,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        overview=ov_dict,
        columns=columns,
        alerts=alert_dicts,
        correlation_charts=correlation_charts,
        heatmap_limit=heatmap_limit,
        heatmap_mobile_limit=mobile_limit,
        interactions=interactions_payload,
        tables=tables or ReportTables(),
        target=_prepare_target(
            target,
            renderer,
        ),
        variables=_prepare_variables(
            column_stats,
            alert_dicts,
        ),
        reproduction_code=code,
        leakage_limit=config.leakage_threshold if config else 0.95,
        repository_url=REPOSITORY_URL,
        package_name=PACKAGE_NAME,
        issue_url=_issue_url(
            ov_dict["reproduction"],
            code,
        ),
        feature_url=_feature_url(code),
        font_faces=_font_face_css(),
        favicon_b64=_load_asset_b64("favicon.svg"),
        logo_mark=_load_text("logo-mark.svg"),
        brand_name=BRAND_NAME,
    )


def _load_text(filename: str) -> str:
    path = _TEMPLATE_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _load_asset_b64(filename: str) -> str:
    path = _TEMPLATE_DIR / filename
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _font_face_css() -> str:
    """Build @font-face rules with the fonts embedded as base64."""
    rules = []
    for family, weight, filename in _FONTS:
        data = _load_asset_b64(f"fonts/{filename}")
        if not data:
            continue
        rules.append(
            f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:normal;'
            f'font-display:swap;src:url(data:font/woff;base64,{data}) format("woff")}}',
        )
    return "\n".join(rules)


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    env.filters["format_number"] = _format_number
    env.filters["format_pct"] = _format_pct
    env.filters["format_float"] = _format_float
    env.filters["humanize"] = _humanize
    env.filters["shorten"] = _shorten
    env.filters["alert_value"] = _format_alert_value
    env.filters["compact"] = _format_compact
    return env


def _issue_url(
    reproduction: dict[str, str],
    code: str,
) -> str:
    """Build a new-issue link with the bug report template filled in."""
    unknown = "unknown"
    environment = {
        "shirabe-profiling version": reproduction.get(
            "shirabe_profiling_version",
            unknown,
        ),
        "polars version": reproduction.get(
            "polars_version",
            unknown,
        ),
        "Python version": reproduction.get(
            "python_version",
            unknown,
        ),
        "OS": reproduction.get(
            "platform",
            unknown,
        ),
    }
    body = "\n".join(
        [
            "## Description",
            "",
            "",
            "## Steps to Reproduce",
            "",
            "```python",
            code,
            "```",
            "",
            "## Expected Behavior",
            "",
            "",
            "## Actual Behavior",
            "",
            "",
            "## Environment",
            "",
            *(f"- **{label}**: {value}" for label, value in environment.items()),
            "",
            "<!-- Paste the details that you copied from the report below. -->",
        ],
    )
    query = urlencode(
        {"labels": "bug", "body": body},
        quote_via=quote,
    )
    return f"{REPOSITORY_URL}/issues/new?{query}"


def _feature_url(code: str) -> str:
    """Build a new-issue link with the feature request template filled in."""
    body = "\n".join(
        [
            "## Problem",
            "",
            "",
            "## Proposed Solution",
            "",
            "```python",
            code,
            "```",
            "",
            "## Alternatives Considered",
            "",
        ],
    )
    query = urlencode(
        {"labels": "enhancement", "body": body},
        quote_via=quote,
    )
    return f"{REPOSITORY_URL}/issues/new?{query}"


def _format_compact(value: Any) -> str:
    """Format a number for a narrow table cell."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value == 0.0 or not math.isfinite(value):
            return f"{value:g}"
        return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.4g}"
    return str(value)


def _prepare_variables(
    column_stats: dict[str, ColumnStats],
    alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build one summary row per column for the variables table."""
    alert_counts: dict[str, int] = {}
    for alert in alerts:
        names = [alert["column"], (alert["details"] or {}).get("column_b")]
        for name in names:
            if name:
                alert_counts[name] = (
                    alert_counts.get(
                        name,
                        0,
                    )
                    + 1
                )

    return [
        {
            "index": index,
            "name": name,
            "type": stats.column_type.name,
            "missing_pct": stats.missing_pct,
            "missing_count": stats.missing_count,
            "distinct": getattr(stats, "distinct_count", None),
            "min": getattr(stats, "min", None),
            "max": getattr(stats, "max", None),
            "mean": getattr(stats, "mean", None),
            "alerts": alert_counts.get(
                name,
                0,
            ),
        }
        for index, (name, stats) in enumerate(column_stats.items())
    ]


def _format_alert_value(alert: dict[str, Any]) -> str:
    """Format an alert value in the unit that fits its alert type."""
    kind = alert["alert_type"]
    value = alert["value"]
    if kind in ("SKEWED", "HIGH_CORRELATION", "TARGET_LEAKAGE"):
        return f"{value:.2f}"
    if kind == "UNIFORM":
        return f"p = {value:.3f}"
    if kind == "CONSTANT":
        return f"{int(value)} distinct"
    return _format_pct(value)


_LONG_FLOAT = re.compile(r"^-?\d+\.\d{3,}$")


def _shorten(value: Any) -> str:
    """Round long decimal strings to two places and leave other text as it is."""
    text = str(value)
    if _LONG_FLOAT.match(text):
        return f"{float(text):.2f}"
    return text


def _humanize(value: Any) -> str:
    return (
        str(value)
        .replace(
            "_",
            " ",
        )
        .title()
    )


def _format_number(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _format_pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        pct = float(value) * 100
        if 0 < pct < 0.1:
            return "<0.1%"
        return f"{pct:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _format_float(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.4f}"
    except (TypeError, ValueError):
        return str(value)


_ALERT_ROWS = {
    "HIGH_MISSING": "Missing",
    "CONSTANT": "Distinct",
    "HIGH_CARDINALITY": "Distinct",
    "HIGH_ZEROS": "Zeros",
    "SKEWED": "Skewness",
    "IMBALANCED": "Imbalance",
}


def _alert_label(alert: Alert) -> str:
    return alert.alert_type.name.replace(
        "_",
        " ",
    ).title()


def _alerts_by_column(alerts: list[Alert]) -> dict[str, list[Alert]]:
    """Group the alerts by column. A pair alert counts for both columns of the pair."""
    by_column: dict[str, list[Alert]] = {}
    for alert in alerts:
        names = [alert.column, alert.details.get("column_b")]
        for name in dict.fromkeys(name for name in names if isinstance(name, str)):
            by_column.setdefault(
                name,
                [],
            ).append(alert)
    return by_column


def _alert_tags(
    column: str,
    alerts: list[Alert],
) -> list[dict[str, str]]:
    """Build one tag for each alert type, with the partner columns of a pair in its title."""
    grouped: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        tag = grouped.setdefault(
            alert.alert_type.name,
            {
                "type": alert.alert_type.name,
                "label": _alert_label(alert),
                "partners": [],
            },
        )
        other = alert.details.get("column_b")
        if isinstance(other, str):
            partner = other if alert.column == column else alert.column
            if partner and partner not in tag["partners"]:
                tag["partners"].append(partner)
    return [
        {
            "type": tag["type"],
            "label": tag["label"],
            "title": f"Alert: {tag['label']}"
            + (f" with {', '.join(tag['partners'])}" if tag["partners"] else ""),
        }
        for tag in grouped.values()
    ]


def _prepare_columns(
    column_stats: dict[str, ColumnStats],
    renderer: ChartRenderer,
    skew: list[dict[str, Any]] | None = None,
    alerts: list[Alert] | None = None,
    skew_limit: float = 2.0,
) -> dict[str, dict[str, Any]]:
    skewed = {entry["column"]: entry for entry in skew or []}
    by_column = _alerts_by_column(alerts or [])
    columns: dict[str, dict[str, Any]] = {}
    for idx, (col_name, stats) in enumerate(column_stats.items()):
        col_dict = asdict(stats)
        col_dict["column_type"] = stats.column_type.name
        col_dict["alerts"] = _alert_tags(
            col_name,
            by_column.get(
                col_name,
                [],
            ),
        )
        col_dict["alert_rows"] = {
            _ALERT_ROWS[alert.alert_type.name]: _alert_label(alert)
            for alert in by_column.get(
                col_name,
                [],
            )
            if alert.alert_type.name in _ALERT_ROWS
        }
        col_dict["extra_rows"] = []
        col_dict["chart_html"] = _chart_for_column(
            stats,
            renderer,
            idx,
            col_name,
        )
        col_dict["views"] = [
            _base_view(
                col_dict,
                idx,
                col_name,
            ),
        ]
        if col_name in skewed and col_dict["chart_html"]:
            col_dict["views"] = _skew_views(
                skewed[col_name],
                renderer,
                idx,
                col_name,
                col_dict,
                skew_limit,
            )
        columns[col_name] = col_dict
    return columns


_VIEW_LABELS = {
    "NUMERIC": "Distribution",
    "CATEGORICAL": "Top Values",
    "BOOLEAN": "Distribution",
    "DATETIME": "Timeline",
    "TEXT": "Summary",
}

_UNCHANGED_FIELDS = {
    "Missing": "missing_count",
    "Distinct": "distinct_count",
    "Zeros": "zeros_count",
}


def _base_view(
    col_dict: dict[str, Any],
    idx: int,
    name: str,
) -> dict[str, Any]:
    """Build the first tab of every column, which shows the column as it is."""
    return {
        "key": "original",
        "label": _VIEW_LABELS.get(
            col_dict["column_type"],
            "Distribution",
        ),
        "chart_id": f"col_chart_{idx}",
        "chart_name": name,
        "chart_html": col_dict["chart_html"],
        "stats": None,
        "ok": False,
    }


def _view_flags(
    original: dict[str, Any],
    stats: dict[str, Any],
    skew_value: float,
    limit: float,
) -> dict[str, str]:
    """Keep an alert mark on a row only while the row still holds the original value."""
    flags = {
        row: label
        for row, label in original["alert_rows"].items()
        if row in _UNCHANGED_FIELDS
        and stats[_UNCHANGED_FIELDS[row]] == original[_UNCHANGED_FIELDS[row]]
    }
    if abs(skew_value) > limit:
        flags["Skewness"] = "Skewed"
    return flags


_SKEW_VIEWS = (
    ("log1p", "log1p", "{name} after log1p"),
    ("yeojohnson", "Yeo-Johnson", "{name} after Yeo-Johnson"),
    ("nonzero", "Non-zero", "{name}, non-zero values after log1p"),
)


def _skew_views(
    entry: dict[str, Any],
    renderer: ChartRenderer,
    idx: int,
    name: str,
    original: dict[str, Any],
    limit: float,
) -> list[dict[str, Any]]:
    """Build the chart tabs for a skewed column: the original, then each transform."""
    views: list[dict[str, Any]] = [
        _base_view(
            original,
            idx,
            name,
        ),
    ]
    for key, label, title in _SKEW_VIEWS:
        variant = entry.get(key)
        if not variant:
            continue
        chart_id = f"col_chart_{idx}_{key}"
        chart_html = _chart_for_column(
            variant["numeric"],
            renderer,
            idx,
            name,
            div_id=chart_id,
            title=title.format(name=name),
        )
        if not chart_html:
            continue
        stats = asdict(variant["numeric"])
        stats["column_type"] = "NUMERIC"
        stats["alerts"] = []
        stats["alert_rows"] = _view_flags(
            original,
            stats,
            variant["skew_value"],
            limit,
        )
        stats["extra_rows"] = _skew_extra_rows(variant)
        views.append(
            {
                "key": key,
                "label": label,
                "chart_id": chart_id,
                "chart_name": f"{name} {label}",
                "chart_html": chart_html,
                "stats": stats,
                "ok": bool(variant.get("ok")),
            },
        )
    return views


def _skew_extra_rows(variant: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    if variant.get("power"):
        rows.append(["Power", variant["power"]])
    if variant.get("zeros"):
        rows.append(["Zeros set aside", variant["zeros"]])
    return rows


def _chart_for_column(
    stats: ColumnStats,
    renderer: ChartRenderer,
    idx: int,
    name: str,
    div_id: str | None = None,
    title: str | None = None,
) -> str:
    div_id = div_id or f"col_chart_{idx}"

    if isinstance(stats, DatetimeStats) and stats.timeline:
        return renderer.histogram(
            div_id,
            [point["label"] for point in stats.timeline],
            [point["count"] for point in stats.timeline],
            title=title or f"{name} by {stats.timeline_unit}",
        )

    if isinstance(stats, NumericStats) and stats.histogram:
        labels = [str(round(h["breakpoint"], 2)) for h in stats.histogram]
        values = [h["count"] for h in stats.histogram]
        return renderer.histogram(
            div_id,
            labels,
            values,
            title=title or f"{name}'s Distribution",
        )

    if isinstance(stats, CategoricalStats) and stats.top_values:
        labels = [str(tv["value"]) for tv in stats.top_values]
        values = [tv["count"] for tv in stats.top_values]
        if stats.other_values is not None:
            labels.append("Other")
            values.append(stats.other_values.count)
        return renderer.bar_horizontal(
            div_id,
            labels,
            values,
            title=f"{name}'s Top Values",
        )

    if isinstance(stats, BooleanStats):
        labels, values = [], []
        if stats.true_count > 0:
            labels.append("True")
            values.append(stats.true_count)
        if stats.false_count > 0:
            labels.append("False")
            values.append(stats.false_count)
        if stats.missing_count > 0:
            labels.append("Missing")
            values.append(stats.missing_count)
        if labels:
            return renderer.pie(
                div_id,
                labels,
                values,
                title=f"{name}'s Distribution",
            )

    return ""


_PAIR_LIST_FROM = 6
_PAIRS_WITH_HEATMAP = 10
_PAIRS_WITHOUT_HEATMAP = 30

_CORRELATION_ORDER = ("phik", "pearson", "spearman", "cramers_v", "kendall")

_SYMMETRIC_RANGE: dict[str, tuple[float, float]] = {
    "pearson": (-1.0, 1.0),
    "spearman": (-1.0, 1.0),
    "kendall": (-1.0, 1.0),
    "cramers_v": (0.0, 1.0),
    "phik": (0.0, 1.0),
}


def _prepare_correlation_charts(
    correlations: dict[str, CorrelationResult],
    renderer: ChartRenderer,
    heatmap_limit: int = 100,
    mobile_limit: int = 20,
) -> list[dict[str, Any]]:
    """Build one entry per method, most useful method first.

    A matrix with more than heatmap_limit columns gets no heatmap, only its strongest pairs.
    A matrix with more than mobile_limit columns hides its heatmap on a narrow screen.
    """
    rank = {method: index for index, method in enumerate(_CORRELATION_ORDER)}
    methods = sorted(
        correlations,
        key=lambda method: rank.get(
            method,
            len(rank),
        ),
    )

    charts: list[dict[str, Any]] = []
    for method in methods:
        matrix = correlations[method].matrix
        labels = matrix["column"].to_list()
        data = matrix.drop("column").to_numpy().tolist()

        div_id = f"corr_{method}"
        display_name = method.replace(
            "_",
            " ",
        ).title()
        shown = len(labels) <= heatmap_limit
        chart_html = ""
        if shown:
            chart_html = renderer.heatmap(
                div_id,
                labels,
                labels,
                data,
                title=f"{display_name} Correlation",
                value_range=_SYMMETRIC_RANGE.get(method),
            )
        mobile_hidden = shown and len(labels) > mobile_limit
        limit = _PAIRS_WITHOUT_HEATMAP if mobile_hidden or not shown else _PAIRS_WITH_HEATMAP
        pairs = (
            _strongest_pairs(
                labels,
                data,
                limit,
            )
            if len(labels) >= _PAIR_LIST_FROM
            else []
        )
        charts.append(
            {
                "key": method,
                "name": display_name,
                "div_id": div_id,
                "chart_html": chart_html,
                "size": len(labels),
                "mobile_hidden": mobile_hidden,
                "pairs": pairs,
            },
        )
    return charts


def _strongest_pairs(
    labels: list[str],
    data: list[list[float]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return the column pairs with the largest absolute value, strongest first."""
    pairs = [
        (labels[i], labels[j], data[i][j])
        for i in range(len(labels))
        for j in range(i + 1, len(labels))
        if not math.isnan(data[i][j])
    ]
    pairs.sort(
        key=lambda pair: abs(pair[2]),
        reverse=True,
    )
    return [{"a": a, "b": b, "value": round(value, 3)} for a, b, value in pairs[:limit]]


def _prepare_target(
    target: TargetAnalysis | None,
    renderer: ChartRenderer,
) -> dict[str, Any] | None:
    """Build the Target section: the summary, the ranking, and one chart per column."""
    if target is None:
        return None

    summary = target.summary
    percent = summary.task == "classification"
    charts = [
        {
            "column": item.column,
            "association": item.association,
            "chart_html": renderer.breakdown(
                f"target_chart_{index}",
                [b.label for b in item.bins],
                [b.count for b in item.bins],
                [b.value for b in item.bins],
                summary.value_label,
                summary.overall,
                percent,
            ),
        }
        for index, item in enumerate(target.breakdowns)
        if item.bins
    ]
    skew = summary.stats.get("skew")
    log_hint = (
        skew is not None
        and summary.log_skew is not None
        and abs(skew) > 1
        and abs(summary.log_skew) < abs(skew)
    )
    return {
        "summary": asdict(summary),
        "percent": percent,
        "links": [asdict(link) for link in target.links],
        "charts": charts,
        "missing_links": [asdict(link) for link in target.missing_links],
        "skipped": target.skipped,
        "log_hint": log_hint,
    }


def _prepare_interactions(
    interactions: InteractionData | None,
) -> dict[str, Any] | None:
    """Serialize InteractionData to a template-friendly dict with JSON payloads."""
    if interactions is None:
        return None

    boxplot_serialized: dict[str, dict[str, list[dict]]] = {}
    for cat_col, num_map in interactions.boxplot_stats.items():
        boxplot_serialized[cat_col] = {}
        for num_col, groups in num_map.items():
            boxplot_serialized[cat_col][num_col] = [asdict(g) for g in groups]

    return {
        "numeric_columns": interactions.numeric_columns,
        "categorical_columns": interactions.categorical_columns,
        "numeric_data_json": json.dumps(
            interactions.numeric_data,
            ensure_ascii=False,
        ),
        "boxplot_stats_json": json.dumps(
            boxplot_serialized,
            ensure_ascii=False,
        ),
        "sampled": interactions.sampled,
        "total_rows": interactions.total_rows,
        "sample_size": interactions.sample_size,
    }
