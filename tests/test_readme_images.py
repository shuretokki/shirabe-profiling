# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

SCRIPT = Path(__file__).parent.parent / "scripts" / "readme_images.py"
spec = importlib.util.spec_from_file_location(
    "readme_images",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None
readme_images = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = readme_images
spec.loader.exec_module(readme_images)

BACKGROUND = (9, 20, 19)


def _picture(
    path: Path,
    content_bottom: int | None,
    height: int = 2400,
    margin: int = 0,
) -> Path:
    image = Image.new(
        "RGB",
        (1280, height),
        BACKGROUND,
    )
    if content_bottom is not None:
        ImageDraw.Draw(image).rectangle(
            (margin, 40, 1279, content_bottom - 1),
            fill=(220, 236, 229),
        )
    image.save(path)
    return path


class TestCrop:
    def test_cuts_the_picture_just_below_the_content(self, tmp_path: Path):
        raw = _picture(
            tmp_path / "raw.png",
            600,
        )
        size = readme_images.crop(
            raw,
            tmp_path / "out.png",
        )
        assert size == (1280, 600 + readme_images.BOTTOM_PAD)
        assert Image.open(tmp_path / "out.png").size == size

    def test_two_pictures_with_different_content_get_different_heights(self, tmp_path: Path):
        short = readme_images.crop(
            _picture(
                tmp_path / "short.png",
                500,
            ),
            tmp_path / "short-out.png",
        )
        tall = readme_images.crop(
            _picture(
                tmp_path / "tall.png",
                900,
            ),
            tmp_path / "tall-out.png",
        )
        assert tall[1] - short[1] == 400

    def test_webp_output_keeps_every_pixel(self, tmp_path: Path):
        raw = _picture(
            tmp_path / "raw.png",
            600,
        )
        size = readme_images.crop(
            raw,
            tmp_path / "out.webp",
        )
        saved = Image.open(tmp_path / "out.webp")
        assert saved.format == "WEBP"
        assert saved.size == size
        original = Image.open(raw).convert("RGB").crop((0, 0, *size))
        assert (
            ImageChops.difference(
                saved.convert("RGB"),
                original,
            ).getbbox()
            is None
        )

    def test_keeps_the_width(self, tmp_path: Path):
        raw = _picture(
            tmp_path / "raw.png",
            300,
        )
        width, _ = readme_images.crop(
            raw,
            tmp_path / "out.png",
        )
        assert width == readme_images.WIDTH

    def test_content_that_fills_the_window_is_cut_with_a_warning(
        self,
        tmp_path: Path,
        capsys,
    ):
        raw = _picture(
            tmp_path / "raw.png",
            1000,
            height=1000,
            margin=100,
        )
        size = readme_images.crop(
            raw,
            tmp_path / "out.png",
        )
        assert size == (1280, 1000)
        assert "is cut at 1000 pixels" in capsys.readouterr().out

    def test_a_blank_picture_keeps_its_full_height(self, tmp_path: Path):
        raw = _picture(
            tmp_path / "raw.png",
            None,
            height=700,
        )
        size = readme_images.crop(
            raw,
            tmp_path / "out.png",
        )
        assert size == (1280, 700)
