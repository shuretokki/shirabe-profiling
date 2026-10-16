# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "add_commas.py"
spec = importlib.util.spec_from_file_location(
    "add_commas",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None
add_commas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(add_commas)


def fix(
    source: str,
    min_args: int = 2,
) -> str:
    return add_commas.add_commas(
        source,
        add_commas.find_spots(
            source,
            min_args,
        ),
    )


class TestCalls:
    def test_two_arguments_get_a_comma(self):
        assert fix("x = f(a, b)\n") == "x = f(a, b,)\n"

    def test_keyword_arguments_count(self):
        assert fix("x = f(a, seed=1)\n") == "x = f(a, seed=1,)\n"

    def test_one_argument_is_left_alone(self):
        assert fix("x = f(a)\n") == "x = f(a)\n"

    def test_builtins_are_left_alone(self):
        source = "x = isinstance(a, int)\ny = range(0, 5, 1)\n"

        assert fix(source) == source

    def test_methods_with_a_builtin_name_still_count(self):
        assert fix("x = obj.max(a, b)\n") == "x = obj.max(a, b,)\n"

    def test_existing_comma_is_kept(self):
        source = "x = f(a, b,)\n"

        assert fix(source) == source

    def test_space_before_the_closing_bracket(self):
        assert fix("x = f(a, b )\n") == "x = f(a, b, )\n"

    def test_nested_calls_each_get_a_comma(self):
        assert fix("x = f(g(a, b), c)\n") == "x = f(g(a, b,), c,)\n"

    def test_calls_that_span_lines_are_left_to_ruff(self):
        source = "x = f(\n    a,\n    b\n)\n"

        assert fix(source) == source

    def test_calls_inside_an_f_string_are_left_alone(self):
        source = 'x = f"{g(a, b)}"\n'

        assert fix(source) == source

    def test_non_ascii_text_before_the_call(self):
        assert fix('x = "é" + f(a, b)\n') == 'x = "é" + f(a, b,)\n'

    def test_list_and_dict_literals_are_left_alone(self):
        source = "x = [1, 2, 3]\ny = {'a': 1, 'b': 2}\n"

        assert fix(source) == source

    def test_threshold_is_an_option(self):
        assert (
            fix(
                "x = f(a, b)\n",
                min_args=3,
            )
            == "x = f(a, b)\n"
        )
        assert (
            fix(
                "x = f(a, b, c)\n",
                min_args=3,
            )
            == "x = f(a, b, c,)\n"
        )


class TestSignatures:
    def test_two_parameters_get_a_comma(self):
        assert fix("def f(a, b):\n    pass\n") == "def f(a, b,):\n    pass\n"

    def test_return_annotation_is_kept(self):
        assert fix("def f(a: int, b: int) -> int:\n    return a\n") == (
            "def f(a: int, b: int,) -> int:\n    return a\n"
        )

    def test_self_does_not_count(self):
        source = "class A:\n    def f(self, a):\n        pass\n"

        assert fix(source) == source

    def test_self_and_two_parameters(self):
        source = "class A:\n    def f(self, a, b):\n        pass\n"

        assert fix(source) == "class A:\n    def f(self, a, b,):\n        pass\n"

    def test_one_parameter_is_left_alone(self):
        source = "def f(a):\n    pass\n"

        assert fix(source) == source

    def test_defaults_with_brackets(self):
        assert fix("def f(a=(1, 2), b=[3]):\n    pass\n") == (
            "def f(a=(1, 2), b=[3],):\n    pass\n"
        )

    def test_async_functions(self):
        assert fix("async def f(a, b):\n    pass\n") == "async def f(a, b,):\n    pass\n"


class TestProgram:
    def test_second_run_adds_nothing(self):
        once = fix("x = f(g(a, b), c)\ndef h(a, b):\n    pass\n")

        assert fix(once) == once

    def test_fix_writes_the_file(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text(
            "x = f(a, b)\n",
            encoding="utf-8",
        )

        code = add_commas.main([str(target)])

        assert code == 0
        assert target.read_text(encoding="utf-8") == "x = f(a, b,)\n"

    def test_check_lists_the_lines_and_fails(
        self,
        tmp_path,
        capsys,
    ):
        target = tmp_path / "sample.py"
        target.write_text(
            "x = f(a, b)\n",
            encoding="utf-8",
        )

        code = add_commas.main(["--check", str(target)])

        assert code == 1
        assert target.read_text(encoding="utf-8") == "x = f(a, b)\n"
        output = capsys.readouterr().out
        assert "sample.py:1: x = f(a, b)" in output
        assert "just commas" in output

    def test_check_passes_on_clean_files(self, tmp_path):
        target = tmp_path / "sample.py"
        target.write_text(
            "x = f(a)\n",
            encoding="utf-8",
        )

        assert add_commas.main(["--check", str(target)]) == 0

    @pytest.mark.parametrize(
        "folder",
        ["src", "tests", "scripts"],
    )
    def test_the_project_follows_its_own_rule(self, folder):
        root = SCRIPT.parent.parent / folder

        assert add_commas.main(["--check", str(root)]) == 0
