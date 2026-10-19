# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Time one profiling tool on one table, in a fresh process.

The driver in run.py starts this script once for each tool and table.
The script reads the table from a Parquet file, runs the tool once as a warm-up,
then runs it again and times each run. It writes the report to a temporary file.
It prints one line that starts with RESULT and holds the numbers as JSON.
"""

from __future__ import annotations

import argparse
import json
import resource
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

SLOW_WARMUP_SECONDS = 60.0

PACKAGES = {
    "shirabe": ["shirabe-profiling", "polars"],
    "ydata": ["fg-data-profiling", "pandas"],
    "skrub": ["skrub", "polars"],
}


def current_rss_mb() -> float:
    """Return the resident memory of this process in megabytes."""
    with Path("/proc/self/statm").open(encoding="utf-8") as handle:
        pages = int(handle.read().split()[1])
    return pages * resource.getpagesize() / 1_000_000


def load(tool: str, path: Path):
    """Read the table in the form that the tool expects."""
    if tool == "ydata":
        import pandas as pd

        return pd.read_parquet(path)
    import polars as pl

    return pl.read_parquet(path)


def make_runner(tool: str, mode: str, table, target: Path):
    """Return a function that makes the report once and writes it to the target."""
    if tool == "shirabe":
        from shirabe_profiling import ProfileReport

        return lambda: ProfileReport(table, mode=mode).to_html(target)
    if tool == "ydata":
        from data_profiling import ProfileReport

        minimal = mode == "minimal"
        return lambda: ProfileReport(
            table,
            minimal=minimal,
            progress_bar=False,
        ).to_file(target)
    if tool == "skrub":
        from skrub import TableReport

        return lambda: TableReport(table).write_html(target)
    msg = f"unknown tool {tool!r}"
    raise SystemExit(msg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Time one profiling tool on one table.")
    parser.add_argument("--tool", required=True, choices=sorted(PACKAGES))
    parser.add_argument("--mode", default="default")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    table = load(args.tool, args.data)
    rows, columns = (table.shape[0], table.shape[1])
    after_load = current_rss_mb()

    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "report.html"
        run = make_runner(args.tool, args.mode, table, target)

        start = time.perf_counter()
        run()
        warmup = time.perf_counter() - start

        timings: list[float] = []
        runs = 0 if warmup > SLOW_WARMUP_SECONDS else args.runs
        for _ in range(runs):
            start = time.perf_counter()
            run()
            timings.append(time.perf_counter() - start)
        report_mb = target.stat().st_size / 1_000_000

    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        "rows": rows,
        "columns": columns,
        "warmup_s": round(warmup, 3),
        "runs_s": [round(value, 3) for value in timings],
        "peak_rss_mb": round(peak_kb * 1024 / 1_000_000, 1),
        "rss_after_load_mb": round(after_load, 1),
        "report_mb": round(report_mb, 2),
        "versions": {name: version(name) for name in PACKAGES[args.tool]},
    }
    print("RESULT " + json.dumps(result))


if __name__ == "__main__":
    main()
