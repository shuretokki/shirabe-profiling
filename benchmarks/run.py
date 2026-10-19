# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Benchmark shirabe-profiling against other profiling tools.

It builds the tables, runs each tool on each table in its own process,
stops a run that takes too long or uses too much memory, and writes the results.
Run it from the repository root: uv run python benchmarks/run.py
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import polars as pl

from shirabe_profiling.datasets import make_homes

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WORKER = ROOT / "worker.py"
AMES_URL = "https://api.openml.org/data/v1/get_csv/21754539"

TOOLS = {
    "shirabe complete": ("shirabe", "complete", []),
    "shirabe overview": ("shirabe", "overview", []),
    "ydata default": ("ydata", "default", ["--with", "fg-data-profiling", "--with", "pyarrow"]),
    "ydata minimal": ("ydata", "minimal", ["--with", "fg-data-profiling", "--with", "pyarrow"]),
    "skrub": ("skrub", "default", ["--with", "skrub", "--with", "polars", "--with", "pyarrow"]),
}


def prepare(name: str) -> Path:
    """Write the table to a Parquet file, once, and return its path."""
    DATA.mkdir(exist_ok=True)
    path = DATA / f"{name}.parquet"
    if path.exists():
        return path
    if name == "ames":
        csv = DATA / "ames.csv"
        if not csv.exists():
            import urllib.request

            urllib.request.urlretrieve(AMES_URL, csv)
        pl.read_csv(
            csv,
            null_values=["NA"],
            infer_schema_length=None,
        ).write_parquet(path)
        return path
    rows = int(name.removeprefix("homes-").removesuffix("k")) * 1000
    make_homes(n=rows).write_parquet(path)
    return path


def command(tool: str, path: Path, runs: int) -> list[str]:
    family, mode, extra = TOOLS[tool]
    args = ["--tool", family, "--mode", mode, "--data", str(path), "--runs", str(runs)]
    if not extra:
        return ["uv", "run", "python", str(WORKER), *args]
    return ["uv", "run", "--no-project", "--isolated", *extra, "python", str(WORKER), *args]


def tree_rss_mb(root_pid: int) -> float:
    """Return the resident memory of a process and all of its children, in megabytes."""
    children: dict[int, list[int]] = {}
    sizes: dict[int, int] = {}
    page = os.sysconf("SC_PAGE_SIZE")
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            statm = (entry / "statm").read_text(encoding="utf-8")
        except OSError:
            continue
        pid = int(entry.name)
        parent = int(stat.rsplit(")", 1)[1].split()[1])
        children.setdefault(parent, []).append(pid)
        sizes[pid] = int(statm.split()[1]) * page
    total, stack = 0, [root_pid]
    while stack:
        pid = stack.pop()
        total += sizes.get(pid, 0)
        stack.extend(children.get(pid, []))
    return total / 1_000_000


def run_worker(
    cmd: list[str],
    timeout: float,
    memory_mb: float,
) -> dict:
    """Run one worker and watch its time and memory. Return a result with a status."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    start = time.monotonic()
    status = "ok"
    while process.poll() is None:
        time.sleep(0.5)
        if time.monotonic() - start > timeout:
            status = f"stopped after {timeout:.0f} s"
        elif tree_rss_mb(process.pid) > memory_mb:
            status = f"stopped at {memory_mb:.0f} MB of memory"
        if status != "ok":
            os.killpg(process.pid, signal.SIGKILL)
            break
    out, err = process.communicate()
    if status != "ok":
        return {"status": status}
    line = next((ln for ln in out.splitlines() if ln.startswith("RESULT ")), None)
    if process.returncode != 0 or line is None:
        return {"status": "error", "error": err.strip().splitlines()[-1] if err.strip() else ""}
    return {"status": "ok", **json.loads(line.removeprefix("RESULT "))}


def first_cell(result: dict) -> str:
    """Return the first-run time cell: the run in a fresh process, as a user sees it."""
    if result["status"] != "ok":
        return result["status"]
    return f"{result['warmup_s']:.1f} s"


def later_cell(result: dict) -> str:
    """Return the median time cell of the runs after the first."""
    if result["status"] != "ok":
        return ""
    runs = result["runs_s"]
    return f"{statistics.median(runs):.2f} s" if runs else "not run (first run over 60 s)"


def summarize(result: dict) -> str:
    """Return a short line for the progress output."""
    if result["status"] != "ok":
        return result["status"]
    later = later_cell(result)
    return f"first run {first_cell(result)}" + (f", later runs {later}" if later else "")


def memory_cell(result: dict) -> str:
    """Return the peak memory cell of the results table for one result."""
    if result["status"] != "ok":
        return result["status"]
    return f"{result['peak_rss_mb']:,.0f} MB"


def git_commit() -> str:
    """Return the short hash of the commit under test, or unknown."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return done.stdout.strip()


def hardware() -> dict:
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines()
            if line.startswith("model name")
        ),
        platform.processor(),
    )
    memory_kb = int(Path("/proc/meminfo").read_text(encoding="utf-8").split()[1])
    return {
        "cpu": cpu,
        "threads": os.cpu_count(),
        "memory_gb": round(memory_kb / 1_000_000, 1),
        "os": platform.platform(),
        "python": platform.python_version(),
    }


def table(
    results: list[dict],
    tools: list[str],
    cell=first_cell,
) -> str:
    names = sorted({row["dataset"] for row in results}, key=lambda n: (n == "ames", n))
    lines = ["| Table | " + " | ".join(tools) + " |", "|" + " --- |" * (len(tools) + 1)]
    for name in names:
        cells = []
        for tool in tools:
            row = next((r for r in results if r["dataset"] == name and r["tool"] == tool), None)
            cells.append(cell(row) if row else "")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the profiling tools.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["homes-10k", "homes-100k", "homes-1000k", "ames"],
    )
    parser.add_argument("--tools", nargs="+", default=list(TOOLS), choices=list(TOOLS))
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds for one worker")
    parser.add_argument(
        "--memory-mb",
        type=float,
        default=3000.0,
        help="memory limit of one worker",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "results.json")
    args = parser.parse_args()

    results: list[dict] = []
    for name in args.tables:
        path = prepare(name)
        for tool in args.tools:
            print(f"{name} / {tool} ...", flush=True)
            result = run_worker(command(tool, path, args.runs), args.timeout, args.memory_mb)
            result.update({"dataset": name, "tool": tool})
            results.append(result)
            print(f"  {summarize(result)}", flush=True)

    existing = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    redone = {(r["dataset"], r["tool"]) for r in results}
    kept = [r for r in existing.get("results", []) if (r["dataset"], r["tool"]) not in redone]
    results = kept + results
    tools = [name for name in TOOLS if any(r["tool"] == name for r in results)]

    payload = {
        "date": date.today().isoformat(),
        "commit": git_commit(),
        "hardware": hardware(),
        "runs": args.runs,
        "timeout_s": args.timeout,
        "memory_limit_mb": args.memory_mb,
        "results": results,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print()
    print("First run in a fresh process")
    print(table(results, tools))
    print()
    print("Median of the later runs")
    print(table(results, tools, later_cell))
    print()
    print("Peak memory of the process")
    print(table(results, tools, memory_cell))
    print(f"\nwrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
