# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw

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


def _striped(height: int) -> Image.Image:
    image = Image.new(
        "RGB",
        (1280, height),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(image)
    for index, top in enumerate(range(0, height, 7)):
        draw.rectangle(
            (0, top, 1279, top + 2),
            fill=(20 + index * 9 % 200, 100, 200 - index * 7 % 150),
        )
    return image


def test_content_bottom_finds_the_end_of_the_content() -> None:
    assert report_scroll.content_bottom(_tall(1500)) == 1500


def test_ease_starts_and_stops_slowly() -> None:
    assert report_scroll.ease(0) == 0
    assert report_scroll.ease(1) == 1
    assert report_scroll.ease(0.1) < 0.1
    assert report_scroll.ease(0.9) > 0.9


class TestScrollTops:
    def test_rests_at_both_ends(self) -> None:
        tops = report_scroll.scroll_tops(
            2000.0,
            glide=100,
            hold=30,
        )
        assert len(tops) == 160
        assert tops[:30] == [0.0] * 30
        assert tops[-30:] == [2000.0] * 30

    def test_never_moves_backwards(self) -> None:
        tops = report_scroll.scroll_tops(
            2000.0,
            glide=100,
            hold=10,
        )
        assert tops == sorted(tops)

    def test_steps_are_small_and_even(self) -> None:
        tops = report_scroll.scroll_tops(
            2000.0,
            glide=1320,
            hold=0,
        )
        steps = [b - a for a, b in zip(tops, tops[1:], strict=False)]
        assert max(steps) < 4.0
        assert steps[0] < max(steps) / 20

    def test_a_short_page_stays_at_the_top(self) -> None:
        tops = report_scroll.scroll_tops(
            0.0,
            glide=50,
            hold=5,
        )
        assert set(tops) == {0.0}


class TestFrames:
    def test_frame_has_the_requested_size(self) -> None:
        frame = report_scroll.render_frame(
            _tall(
                2000,
                height=2000,
            ),
            top=100.0,
            width=640,
            view=360,
        )
        assert frame.size == (640, 360)

    def test_a_fraction_of_a_pixel_changes_the_frame(self) -> None:
        tall = _striped(2000)
        first = report_scroll.render_frame(
            tall,
            100.0,
            1280,
            720,
        )
        half = report_scroll.render_frame(
            tall,
            100.5,
            1280,
            720,
        )
        next_row = report_scroll.render_frame(
            tall,
            101.0,
            1280,
            720,
        )
        assert (
            ImageChops.difference(
                first,
                half,
            ).getbbox()
            is not None
        )
        assert (
            ImageChops.difference(
                half,
                next_row,
            ).getbbox()
            is not None
        )

    def test_the_last_position_stays_inside_the_picture(self) -> None:
        tall = _striped(1000)
        frame = report_scroll.render_frame(
            tall,
            1000.0,
            640,
            360,
        )
        assert frame.size == (640, 360)

    def test_a_short_page_is_padded_to_one_frame(self) -> None:
        short = _tall(
            100,
            height=200,
        )
        padded = report_scroll.with_height(
            short,
            720.0,
        )
        assert padded.height == 720
        assert padded.getpixel((4, 719)) == BACKGROUND

    def test_a_resting_frame_is_drawn_once(self) -> None:
        frames = list(
            report_scroll.frames_for(
                _striped(2000),
                [0.0, 0.0, 0.0, 10.0],
                640,
                360,
            ),
        )
        assert frames[0] is frames[1] is frames[2]
        assert frames[3] is not frames[2]


def test_command_writes_both_videos(tmp_path: Path) -> None:
    command = report_scroll.ffmpeg_command(
        "ffmpeg",
        1280,
        720,
        60,
        tmp_path / "a.mp4",
        tmp_path / "a.webm",
    )
    assert "1280x720" in command
    assert command.count("-vf") == 2
    assert command[-1].endswith("a.webm")
    assert str(tmp_path / "a.mp4") in command


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg is not installed",
)
def test_encode_writes_both_files(tmp_path: Path) -> None:
    mp4 = tmp_path / "scroll.mp4"
    webm = tmp_path / "scroll.webm"
    tall = _striped(1000)
    tops = report_scroll.scroll_tops(
        280.0,
        glide=10,
        hold=2,
    )
    report_scroll.encode(
        report_scroll.frames_for(
            tall,
            tops,
            64,
            36,
        ),
        report_scroll.ffmpeg_command(
            shutil.which("ffmpeg") or "ffmpeg",
            64,
            36,
            10,
            mp4,
            webm,
        ),
    )
    assert mp4.stat().st_size > 0
    assert webm.stat().st_size > 0
