# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "benchmarks" / "run.py"
spec = importlib.util.spec_from_file_location(
    "benchmark_run",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None
benchmark_run = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = benchmark_run
spec.loader.exec_module(benchmark_run)

linux_only = pytest.mark.skipif(
    not Path("/proc/self/statm").exists(),
    reason="needs /proc",
)


def _ok(
    warmup: float = 2.0,
    runs: list[float] | None = None,
    peak: float = 512.0,
) -> dict:
    return {
        "status": "ok",
        "warmup_s": warmup,
        "runs_s": [1.0, 3.0, 2.0] if runs is None else runs,
        "peak_rss_mb": peak,
    }


class TestCells:
    def test_first_run_is_the_warm_up(self) -> None:
        assert benchmark_run.first_cell(_ok(warmup=55.5)) == "55.5 s"

    def test_later_runs_use_the_median(self) -> None:
        assert benchmark_run.later_cell(_ok(runs=[1.0, 3.0, 2.0])) == "2.00 s"

    def test_a_slow_first_run_has_no_later_runs(self) -> None:
        assert "not run" in benchmark_run.later_cell(
            _ok(
                warmup=80.0,
                runs=[],
            ),
        )

    def test_a_stopped_run_shows_why(self) -> None:
        stopped = {"status": "stopped after 900 s"}
        assert benchmark_run.first_cell(stopped) == "stopped after 900 s"
        assert benchmark_run.memory_cell(stopped) == "stopped after 900 s"
        assert benchmark_run.later_cell(stopped) == ""

    def test_memory_has_a_thousands_separator(self) -> None:
        assert benchmark_run.memory_cell(_ok(peak=1358.4)) == "1,358 MB"

    def test_the_progress_line_names_both_times(self) -> None:
        line = benchmark_run.summarize(
            _ok(
                warmup=4.0,
                runs=[2.0],
            ),
        )
        assert line == "first run 4.0 s, later runs 2.00 s"


class TestTable:
    def test_rows_are_tables_and_columns_are_tools(self) -> None:
        results = [
            {"dataset": "ames", "tool": "a", **_ok()},
            {"dataset": "homes-10k", "tool": "a", **_ok(warmup=1.0)},
            {"dataset": "homes-10k", "tool": "b", **_ok(warmup=9.0)},
        ]
        lines = benchmark_run.table(
            results,
            ["a", "b"],
        ).splitlines()
        assert lines[0] == "| Table | a | b |"
        assert lines[2].startswith("| homes-10k | 1.0 s | 9.0 s |")
        assert lines[3] == "| ames | 2.0 s |  |"


class TestCommand:
    def test_shirabe_runs_in_the_project_environment(self) -> None:
        cmd = benchmark_run.command(
            "shirabe complete",
            Path("t.parquet"),
            5,
        )
        assert cmd[:3] == ["uv", "run", "python"]
        assert "--no-project" not in cmd

    def test_another_tool_runs_in_its_own_environment(self) -> None:
        cmd = benchmark_run.command(
            "ydata minimal",
            Path("t.parquet"),
            5,
        )
        assert "--isolated" in cmd
        assert "fg-data-profiling" in cmd
        assert cmd[cmd.index("--mode") + 1] == "minimal"


@linux_only
class TestWatching:
    def test_a_process_tree_has_memory(self) -> None:
        assert benchmark_run.tree_rss_mb(os.getpid()) > 1.0

    def test_a_result_line_is_read(self) -> None:
        code = "print('noise'); print('RESULT {\"x\": 1}')"
        result = benchmark_run.run_worker(
            [sys.executable, "-c", code],
            30,
            5000,
        )
        assert result == {"status": "ok", "x": 1}

    def test_a_failing_worker_reports_an_error(self) -> None:
        code = "raise SystemExit('boom')"
        result = benchmark_run.run_worker(
            [sys.executable, "-c", code],
            30,
            5000,
        )
        assert result["status"] == "error"

    def test_a_slow_worker_is_stopped(self) -> None:
        code = "import time; time.sleep(60)"
        result = benchmark_run.run_worker(
            [sys.executable, "-c", code],
            1,
            5000,
        )
        assert result["status"] == "stopped after 1 s"

    def test_a_worker_that_takes_too_much_memory_is_stopped(self) -> None:
        code = "import time; data = b'x' * 400_000_000; time.sleep(60)"
        result = benchmark_run.run_worker(
            [sys.executable, "-c", code],
            60,
            200,
        )
        assert "memory" in result["status"]
