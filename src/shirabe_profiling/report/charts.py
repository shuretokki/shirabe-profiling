# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Chart rendering abstraction — pluggable backend.

ChartRenderer Protocol defines the contract.
EChartsRenderer is the default implementation.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class ChartRenderer(Protocol):
    """Contract for chart rendering backends.

    Each method returns an HTML string containing a <div> and <script>
    that renders the chart. The div_id must be unique per page.
    """

    def histogram(
        self,
        div_id: str,
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str: ...

    def bar_horizontal(
        self,
        div_id: str,
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str: ...

    def heatmap(
        self,
        div_id: str,
        x_labels: list[str],
        y_labels: list[str],
        data: list[list[float]],
        title: str = "",
        value_range: tuple[float, float] | None = None,
    ) -> str: ...

    def pie(
        self,
        div_id: str,
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str: ...

    def word_cloud(
        self,
        div_id: str,
        words: list[str],
        weights: list[int | float],
        title: str = "",
    ) -> str: ...

    def breakdown(
        self,
        div_id: str,
        labels: list[str],
        counts: list[int],
        values: list[float],
        value_label: str,
        baseline: float,
        percent: bool = False,
    ) -> str: ...


def _token(name: str) -> str:
    """Return a placeholder that the report script replaces with a CSS token."""
    return f"var(--{name})"


class EChartsRenderer:
    """ECharts-based chart renderer. Produces self-contained HTML snippets."""

    CHART_HEIGHT = "300px"
    BREAKDOWN_HEIGHT = "260px"
    HEATMAP_HEIGHT = "400px"
    HEATMAP_CELL = 22
    HEATMAP_DENSE_CELL = 16
    HEATMAP_DENSE_AFTER = 40
    HEATMAP_LABELS_UP_TO = 12
    HEATMAP_MIN_HEIGHT = 400
    HEATMAP_MIN_WIDTH = 600
    TITLE_STYLE = {"fontSize": 13}

    def histogram(
        self,
        div_id: str,
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str:
        option = {
            "title": {"text": title, "left": "center", "textStyle": self.TITLE_STYLE},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "10%", "right": "5%", "bottom": "15%", "top": "15%"},
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"rotate": 30, "fontSize": 10},
            },
            "yAxis": {"type": "value"},
            "series": [
                {
                    "type": "bar",
                    "data": values,
                    "itemStyle": {"color": _token("text")},
                    "barWidth": "90%",
                },
            ],
        }
        return self._wrap(
            div_id,
            option,
            self.CHART_HEIGHT,
        )

    def bar_horizontal(
        self,
        div_id: str,
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str:
        option = {
            "title": {"text": title, "left": "center", "textStyle": self.TITLE_STYLE},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "25%", "right": "10%", "bottom": "10%", "top": "15%"},
            "xAxis": {"type": "value"},
            "yAxis": {
                "type": "category",
                "data": list(reversed(labels)),
                "axisLabel": {"fontSize": 11},
            },
            "series": [
                {
                    "type": "bar",
                    "data": list(reversed(values)),
                    "itemStyle": {"color": _token("text")},
                },
            ],
        }
        return self._wrap(
            div_id,
            option,
            self.CHART_HEIGHT,
        )

    def heatmap(
        self,
        div_id: str,
        x_labels: list[str],
        y_labels: list[str],
        data: list[list[float]],
        title: str = "",
        value_range: tuple[float, float] | None = None,
    ) -> str:
        size = len(x_labels)
        decimals = 3 if size <= 30 else 2
        flat_data = []
        v_min, v_max = float("inf"), float("-inf")
        for row_idx, row in enumerate(data):
            for col_idx, val in enumerate(row):
                flat_data.append([col_idx, row_idx, round(val, decimals)])
                if row_idx != col_idx:
                    v_min = min(v_min, val)
                    v_max = max(v_max, val)

        if value_range is not None:
            v_min, v_max = value_range
        elif v_min == float("inf"):
            v_min, v_max = -1.0, 1.0

        if v_min < 0:
            colors = [_token("info"), _token("surface"), _token("warning")]
        else:
            colors = [_token("surface"), _token("primary")]

        cell = self.HEATMAP_CELL if size <= self.HEATMAP_DENSE_AFTER else self.HEATMAP_DENSE_CELL
        height_px = max(self.HEATMAP_MIN_HEIGHT, size * cell + 170)
        width_px = max(self.HEATMAP_MIN_WIDTH, size * cell + 260)

        option = {
            "title": {"text": title, "left": "center", "textStyle": self.TITLE_STYLE},
            "tooltip": {
                "position": "top",
                "formatter": None,  # replaced below
            },
            "grid": {"left": 10, "right": 90, "top": 50, "bottom": 20, "containLabel": True},
            "xAxis": {
                "type": "category",
                "data": x_labels,
                "splitArea": {"show": True},
                "axisLabel": {"rotate": 45 if size > 8 else 30, "fontSize": 10, "interval": 0},
            },
            "yAxis": {
                "type": "category",
                "data": y_labels,
                "splitArea": {"show": True},
                "axisLabel": {"fontSize": 10, "interval": 0},
            },
            "visualMap": {
                "min": round(v_min, 3),
                "max": round(v_max, 3),
                "calculable": True,
                "orient": "vertical",
                "right": 10,
                "top": "center",
                "inRange": {"color": colors},
            },
            "series": [
                {
                    "type": "heatmap",
                    "data": flat_data,
                    "label": {
                        "show": size <= self.HEATMAP_LABELS_UP_TO,
                        "fontSize": 10,
                        "color": _token("text"),
                        "textBorderColor": _token("editor"),
                        "textBorderWidth": 2,
                    },
                    "emphasis": {"itemStyle": {"borderColor": _token("text"), "borderWidth": 1}},
                },
            ],
        }

        option_json = json.dumps(
            option,
            ensure_ascii=False,
        )
        # inject a JS formatter function, because JSON cannot hold one
        tooltip_fn = (
            f"function(p){{var x={json.dumps(x_labels, ensure_ascii=False)},"
            f"y={json.dumps(y_labels, ensure_ascii=False)};"
            "return x[p.value[0]] + ' vs ' + y[p.value[1]] + ': ' + p.value[2];}"
        )
        option_json = option_json.replace(
            '"formatter": null',
            f'"formatter": {tooltip_fn}',
        )

        return self._script(
            div_id,
            option_json,
            f"{height_px}px",
            min_width=width_px,
        )

    def pie(
        self,
        div_id: str,
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str:
        pie_data = [{"name": lbl, "value": v} for lbl, v in zip(labels, values, strict=True)]
        option = {
            "title": {"text": title, "left": "center", "textStyle": self.TITLE_STYLE},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"orient": "horizontal", "bottom": "0%", "left": "center"},
            "series": [
                {
                    "type": "pie",
                    "radius": ["35%", "60%"],
                    "center": ["50%", "50%"],
                    "data": pie_data,
                    "itemStyle": {"borderColor": _token("editor"), "borderWidth": 2},
                    "label": {"formatter": "{b}: {d}%"},
                },
            ],
        }
        return self._wrap(
            div_id,
            option,
            self.CHART_HEIGHT,
        )

    def word_cloud(
        self,
        div_id: str,
        words: list[str],
        weights: list[int | float],
        title: str = "",
    ) -> str:
        wc_data = [{"name": w, "value": v} for w, v in zip(words, weights, strict=True)]
        option = {
            "title": {"text": title, "left": "center", "textStyle": self.TITLE_STYLE},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
            "series": [
                {
                    "type": "wordCloud",
                    "shape": "circle",
                    "sizeRange": [14, 60],
                    "rotationRange": [0, 0],
                    "rotationStep": 0,
                    "gridSize": 8,
                    "drawOutOfBound": False,
                    "layoutAnimation": True,
                    "textStyle": {
                        "fontFamily": _token("font-ui"),
                        "fontWeight": 600,
                        "color": None,  # replaced below
                    },
                    "data": wc_data,
                },
            ],
        }

        option_json = json.dumps(
            option,
            ensure_ascii=False,
        )
        color_fn = (
            "function(){var c=reportTheme.palette;return c[Math.floor(Math.random()*c.length)];}"
        )
        option_json = option_json.replace(
            '"color": null',
            f'"color": {color_fn}',
        )

        return self._script(
            div_id,
            option_json,
            self.CHART_HEIGHT,
        )

    def breakdown(
        self,
        div_id: str,
        labels: list[str],
        counts: list[int],
        values: list[float],
        value_label: str,
        baseline: float,
        percent: bool = False,
    ) -> str:
        """Draw the rows per group as bars and the target value per group as a line."""
        scale = 100 if percent else 1
        suffix = "%" if percent else ""
        line = [round(value * scale, 2) for value in values]
        option = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"top": 0, "data": ["Rows", value_label], "textStyle": {"fontSize": 11}},
            "grid": {"left": 56, "right": 56, "bottom": 56, "top": 36},
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"rotate": 30, "fontSize": 10, "interval": 0},
            },
            "yAxis": [
                {"type": "value", "splitLine": {"show": False}},
                {
                    "type": "value",
                    "axisLabel": {"formatter": "{value}" + suffix},
                    **({"min": 0, "max": 100} if percent else {}),
                },
            ],
            "series": [
                {
                    "name": "Rows",
                    "type": "bar",
                    "data": counts,
                    "itemStyle": {"color": _token("border")},
                    "barMaxWidth": 36,
                },
                {
                    "name": value_label,
                    "type": "line",
                    "yAxisIndex": 1,
                    "data": line,
                    "symbolSize": 7,
                    "itemStyle": {"color": _token("primary")},
                    "lineStyle": {"color": _token("primary")},
                    "markLine": {
                        "silent": True,
                        "symbol": "none",
                        "label": {"show": False},
                        "lineStyle": {"color": _token("text-muted"), "type": "dashed"},
                        "data": [{"yAxis": round(baseline * scale, 2)}],
                    },
                },
            ],
        }
        return self._wrap(
            div_id,
            option,
            self.BREAKDOWN_HEIGHT,
        )

    @staticmethod
    def _wrap(
        div_id: str,
        option: dict,
        height: str,
    ) -> str:
        return EChartsRenderer._script(
            div_id,
            json.dumps(
                option,
                ensure_ascii=False,
            ),
            height,
        )

    @staticmethod
    def _script(
        div_id: str,
        option_json: str,
        height: str,
        min_width: int | None = None,
    ) -> str:
        script = f"<script>reportTheme.mount('{div_id}', {option_json});</script>"
        if min_width is None:
            return f'<div id="{div_id}" style="width:100%;height:{height}"></div>\n{script}'
        style = f"width:100%;min-width:{min_width}px;height:{height}"
        chart = f'<div id="{div_id}" style="{style}"></div>'
        return f'<div class="chart-scroll">{chart}</div>\n{script}'
