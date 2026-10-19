# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Fast, Polars-native data profiling."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal

import polars as pl  # noqa: TC002 — used at runtime

from shirabe_profiling.alerts import Alert, AlertType, alert_order, check_quality
from shirabe_profiling.analyzers import ColumnStats, analyze
from shirabe_profiling.config import ProfileConfig
from shirabe_profiling.correlations import CorrelationResult, compute_correlations
from shirabe_profiling.dataset_overview import DatasetOverview, compute_overview
from shirabe_profiling.ingest import ingest
from shirabe_profiling.interactions import InteractionData, compute_interactions
from shirabe_profiling.report.html import render_html
from shirabe_profiling.reproduction import describe_call
from shirabe_profiling.skew import compute_skew_transforms
from shirabe_profiling.tables import ReportTables, compute_tables
from shirabe_profiling.target import TargetAnalysis, compute_target, target_alerts
from shirabe_profiling.type_inference import ColumnType, infer_types

if TYPE_CHECKING:
    from pathlib import Path

__version__ = "0.1.0"

__all__ = ["ProfileReport", "ProfileConfig", "ColumnType", "AlertType", "Alert"]


def _record_duration(
    reproduction: dict[str, str],
    seconds: float,
) -> None:
    """Add the profiling time to the reproduction details, right after the mode."""
    items = list(reproduction.items())
    position = next((i for i, (key, _) in enumerate(items) if key == "mode"), len(items) - 1) + 1
    items.insert(
        position,
        ("profiling_time", f"{seconds:.2f} s"),
    )
    reproduction.clear()
    reproduction.update(items)


class ProfileReport:
    """Main entry point for data profiling.

    Usage:
        report = ProfileReport(df)
        report = ProfileReport(df, title="My Data")
        report = ProfileReport(df, mode="overview")
    """

    def __init__(
        self,
        source: Any,
        *,
        title: str = "Dataset Report",
        mode: Literal["complete", "overview"] = "complete",
        config: ProfileConfig | None = None,
        **kwargs: Any,
    ) -> None:
        started = time.perf_counter()
        self._call_code: str = describe_call(
            source,
            title=title,
            mode=mode,
            config=config,
            kwargs=kwargs,
        )
        if config is not None:
            self._config = config
        else:
            self._config = ProfileConfig(
                title=title,
                mode=mode,
                **kwargs,
            )

        self._df: pl.DataFrame = ingest(source)
        self._column_types: dict[str, ColumnType] = infer_types(
            self._df,
            self._config,
        )
        self._column_stats: dict[str, ColumnStats] = analyze(
            self._df,
            self._column_types,
            self._config,
        )
        self._overview: DatasetOverview = compute_overview(
            self._df,
            self._column_types,
            self._config,
        )
        self._correlations: dict[str, CorrelationResult] = compute_correlations(
            self._df,
            self._column_types,
            self._config,
        )
        self._interactions: InteractionData | None = compute_interactions(
            self._df,
            self._column_types,
            self._config,
        )
        self._alerts: list[Alert] = check_quality(
            self._column_stats,
            self._overview,
            self._config,
            self._correlations,
        )
        self._target: TargetAnalysis | None = compute_target(
            self._df,
            self._column_types,
            self._config,
        )
        if self._target is not None:
            self._alerts.extend(
                target_alerts(
                    self._target,
                    self._config,
                ),
            )
            self._alerts.sort(key=alert_order)
        self._tables: ReportTables = compute_tables(
            self._df,
            self._column_stats,
            self._config,
        )
        self._skew: list[dict[str, Any]] = compute_skew_transforms(
            self._df,
            self._alerts,
            self._config,
        )
        _record_duration(
            self._overview.reproduction,
            time.perf_counter() - started,
        )

    @property
    def config(self) -> ProfileConfig:
        return self._config

    @property
    def df(self) -> pl.DataFrame:
        return self._df

    @property
    def column_types(self) -> dict[str, ColumnType]:
        return self._column_types

    @property
    def overview(self) -> dict[str, Any]:
        return asdict(self._overview)

    @property
    def alerts(self) -> list[Alert]:
        return self._alerts

    @property
    def stats(self) -> dict[str, dict[str, Any]]:
        return {name: asdict(s) for name, s in self._column_stats.items()}

    @property
    def correlations(self) -> dict[str, CorrelationResult]:
        return self._correlations

    @property
    def interactions(self) -> InteractionData | None:
        return self._interactions

    @property
    def target(self) -> TargetAnalysis | None:
        return self._target

    def to_dict(self) -> dict[str, Any]:
        corr_dict: dict[str, Any] = {}
        for method, cr in self._correlations.items():
            entry: dict[str, Any] = {"matrix": cr.matrix.to_dicts()}
            if cr.pvalues is not None:
                entry["pvalues"] = cr.pvalues.to_dicts()
            corr_dict[method] = entry

        return {
            "title": self._config.title,
            "overview": self.overview,
            "columns": self.stats,
            "alerts": [
                {
                    "column": a.column,
                    "alert_type": a.alert_type.name,
                    "value": a.value,
                    "details": a.details,
                }
                for a in self._alerts
            ],
            "correlations": corr_dict,
            "interactions": self._serialize_interactions(),
            "target": asdict(self._target) if self._target is not None else None,
        }

    def _serialize_interactions(self) -> dict[str, Any] | None:
        if self._interactions is None:
            return None
        bp: dict[str, dict[str, list[dict]]] = {}
        for cat, num_map in self._interactions.boxplot_stats.items():
            bp[cat] = {}
            for num, groups in num_map.items():
                bp[cat][num] = [asdict(g) for g in groups]
        return {
            "numeric_columns": self._interactions.numeric_columns,
            "categorical_columns": self._interactions.categorical_columns,
            "numeric_data": self._interactions.numeric_data,
            "boxplot_stats": bp,
            "sampled": self._interactions.sampled,
            "total_rows": self._interactions.total_rows,
            "sample_size": self._interactions.sample_size,
        }

    def to_html(self, path: str | Path | None = None) -> str:
        html = render_html(
            title=self._config.title,
            version=__version__,
            overview=self._overview,
            column_stats=self._column_stats,
            alerts=self._alerts,
            correlations=self._correlations,
            interactions=self._interactions,
            tables=self._tables,
            target=self._target,
            config=self._config,
            reproduction_code=self._call_code,
            skew=self._skew,
        )
        if path is not None:
            from pathlib import Path as P

            P(path).write_text(
                html,
                encoding="utf-8",
            )

        return html

    def to_json(
        self,
        path: str | Path | None = None,
        indent: int = 2,
    ) -> str:
        data = self.to_dict()
        # turn the ColumnType enum into a string for JSON
        for col_data in data["columns"].values():
            if "column_type" in col_data:
                col_data["column_type"] = col_data["column_type"].name

        output = json.dumps(
            data,
            indent=indent,
            default=str,
            ensure_ascii=False,
        )

        if path is not None:
            from pathlib import Path as P

            P(path).write_text(
                output,
                encoding="utf-8",
            )

        return output

    def __repr__(self) -> str:
        return (
            f"ProfileReport("
            f"title='{self._config.title}', "
            f"rows={self._df.height}, "
            f"columns={self._df.width})"
        )
