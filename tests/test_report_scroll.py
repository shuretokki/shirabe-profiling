# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).parent.parent / "scripts" / "report_scroll.py"
spec = importlib.util.spec_from_file_location(
    "report_scroll",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None
report_scroll = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = report_scroll
spec.loader.exec_module(report_scroll)

BACKGROUND = (9, 20, 19)


def _tall(
    content_bottom: int,
    height: int = 3000,
) -> Image.Image:
    image = Image.new(
        "RGB",
        (1280, height),
        BACKGROUND,
    )
    ImageDraw.Draw(image).rectangle(
        (0, 40, 1279, content_bottom - 1),
        fill=(220, 236, 229),
    )
    return image


def test_content_bottom_finds_the_end_of_the_content() -> None:
    assert report_scroll.content_bottom(_tall(1500)) == 1500


def test_frames_start_at_the_top_and_end_at_the_bottom() -> None:
    frames = report_scroll.make_frames(
        _tall(
            2000,
            height=2000,
        ),
        width=640,
        view=300,
        step=100,
    )
    assert all(frame.size == (640, 300) for frame in frames)
    assert len(frames) >= 3


def test_frames_of_a_short_page_are_one_frame() -> None:
    frames = report_scroll.make_frames(
        _tall(
            200,
            height=200,
        ),
        width=640,
        view=300,
        step=100,
    )
    assert len(frames) == 1


def _striped(height: int) -> Image.Image:
    image = Image.new(
        "RGB",
        (1280, height),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(image)
    for index, top in enumerate(range(0, height, 70)):
        draw.rectangle(
            (0, top, 1279, top + 34),
            fill=(20 + index * 9 % 200, 100, 200 - index * 7 % 150),
        )
    return image


def test_save_gif_writes_an_animated_file(tmp_path: Path) -> None:
    frames = report_scroll.make_frames(
        _striped(2000),
        width=640,
        view=300,
        step=100,
    )
    target = tmp_path / "scroll.gif"
    report_scroll.save_gif(
        frames,
        target,
    )
    with Image.open(target) as gif:
        assert gif.format == "GIF"
        assert getattr(gif, "n_frames", 1) == len(frames)
