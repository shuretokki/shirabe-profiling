# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Make the scrolling GIFs of the report for the docs.

The script takes one tall picture of the whole report for each theme.
It then slides a window down the picture and saves the frames as a GIF.
It uses the same browser and the same sample table as `readme_images.py`.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops

from shirabe_profiling import ProfileReport
from shirabe_profiling.datasets import make_homes

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent),
)

from readme_images import (  # noqa: E402
    BASE_CSS,
    WIDTH,
    Shot,
    capture,
    find_browser,
    page_for,
    work_dir,
)

TALL_HEIGHT = 12000
BOTTOM_PAD = 24
PAUSE_MS = 1500
COLORS = 48

THEMES = {
    "report-scroll": "light",
    "report-scroll-dark": "dark",
}


def content_bottom(image: Image.Image) -> int:
    """Return the row where the content of the page ends."""
    background = image.getpixel((4, image.height - 4))
    box = ImageChops.difference(
        image,
        Image.new(
            "RGB",
            image.size,
            background,
        ),
    ).getbbox()
    return box[3] if box else image.height


def ease(t: float) -> float:
    """Return a smooth start and stop for a value from 0 to 1."""
    return t * t * (3 - 2 * t)


def make_frames(
    tall: Image.Image,
    width: int,
    view: int,
    count: int,
) -> list[Image.Image]:
    """Return the frames of a window that glides from the top to the bottom of the picture."""
    scale = width / tall.width
    scaled = tall.resize(
        (width, round(tall.height * scale)),
        Image.Resampling.LANCZOS,
    ).quantize(
        colors=COLORS,
        dither=Image.Dither.NONE,
    )
    last = max(scaled.height - view, 0)
    if last == 0 or count < 2:
        return [scaled.crop((0, 0, width, view))]
    offsets = [round(last * ease(index / (count - 1))) for index in range(count)]
    return [scaled.crop((0, top, width, top + view)) for top in offsets]


def save_gif(
    frames: list[Image.Image],
    target: Path,
    frame_ms: int,
) -> None:
    durations = [frame_ms] * len(frames)
    durations[0] = PAUSE_MS
    durations[-1] = PAUSE_MS
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Make the scrolling GIFs of the report.")
    parser.add_argument(
        "out",
        type=Path,
        nargs="?",
        default=Path("assets/screenshots"),
        help="folder for the GIFs",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=720,
        help="width of the GIF in pixels",
    )
    parser.add_argument(
        "--view",
        type=int,
        default=450,
        help="height of the GIF in pixels",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=14.0,
        help="time the scroll takes from the top to the bottom",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=20,
        help="frames for each second",
    )
    args = parser.parse_args()
    args.out.mkdir(
        parents=True,
        exist_ok=True,
    )

    browser = find_browser()
    print(f"Browser: {browser}")
    html = ProfileReport(
        make_homes(),
        title="Home Prices Profile",
        target="price",
    ).to_html()
    folder = work_dir(browser)
    try:
        for name, theme in THEMES.items():
            shot = Shot(
                name,
                theme,
                "",
            )
            page = folder / f"{name}.html"
            raw = folder / f"{name}.png"
            page.write_text(
                page_for(
                    html,
                    shot,
                ).replace(
                    "</head>",
                    f"<style>{BASE_CSS}</style></head>",
                    1,
                ),
                encoding="utf-8",
            )
            raw.unlink(missing_ok=True)
            capture(
                browser,
                page,
                raw,
                TALL_HEIGHT,
            )
            image = Image.open(raw).convert("RGB")
            bottom = content_bottom(image)
            if bottom + BOTTOM_PAD > image.height:
                print(f"  warning: the report of {name} is cut at {image.height} pixels")
            tall = image.crop(
                (0, 0, WIDTH, min(bottom + BOTTOM_PAD, image.height)),
            )
            frames = make_frames(
                tall,
                args.width,
                args.view,
                round(args.seconds * args.fps),
            )
            target = args.out / f"{name}.gif"
            save_gif(
                frames,
                target,
                round(1000 / args.fps),
            )
            size = target.stat().st_size / 1_000_000
            print(f"{name}.gif  {args.width}x{args.view}  {len(frames)} frames  {size:.1f} MB")
    finally:
        shutil.rmtree(
            folder,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()
