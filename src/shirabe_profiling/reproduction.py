"""Describe how the user called ProfileReport, for the reproduction code."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any

import polars as pl

from shirabe_profiling.config import ProfileConfig

DEFAULT_TITLE = "Dataset Report"
DEFAULT_MODE = "complete"


def describe_call(
    source: Any,
    *,
    title: str = DEFAULT_TITLE,
    mode: str = DEFAULT_MODE,
    config: ProfileConfig | None = None,
    kwargs: dict[str, Any] | None = None,
) -> str:
    """Return Python code that repeats the ProfileReport call with the same arguments.

    The data source is shown as a name, never as a full path.
    """
    imports = "ProfileConfig, ProfileReport" if config is not None else "ProfileReport"
    lines = [
        f"from shirabe_profiling import {imports}",
        "",
        "report = ProfileReport(",
        f"    {_source_line(source)}",
    ]
    if config is not None:
        lines.extend(_config_lines(config))
    else:
        if title != DEFAULT_TITLE:
            lines.append(f"    title={title!r},")
        if mode != DEFAULT_MODE:
            lines.append(f"    mode={mode!r},")
        lines.extend(f"    {name}={value!r}," for name, value in (kwargs or {}).items())
    lines.extend([")", 'report.to_html("report.html")'])
    return "\n".join(lines)


def _source_line(source: Any) -> str:
    if source is None:
        return "df,  # your data"
    if isinstance(source, (str, Path)):
        return f"{Path(source).name!r},  # your data file, name only"
    if isinstance(source, pl.LazyFrame):
        return "lf,  # your Polars LazyFrame"
    if isinstance(source, pl.DataFrame):
        return "df,  # your Polars DataFrame"
    kind = type(source)
    if kind.__module__.split(".")[0] == "pandas":
        return "df,  # your pandas DataFrame"
    return f"data,  # your {kind.__name__}"


def _config_lines(config: ProfileConfig) -> list[str]:
    defaults = ProfileConfig()
    changed = {
        item.name: getattr(config, item.name)
        for item in fields(ProfileConfig)
        if getattr(config, item.name) != getattr(defaults, item.name)
    }
    if not changed:
        return ["    config=ProfileConfig(),"]
    return [
        "    config=ProfileConfig(",
        *(f"        {name}={value!r}," for name, value in changed.items()),
        "    ),",
    ]
