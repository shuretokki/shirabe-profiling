# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Make the scrolling videos of the report for the docs.

The script takes one tall picture of the whole report for each theme.
It slides a window down the picture and sends every frame to ffmpeg.
ffmpeg writes a WebM file and an MP4 file, and the script saves the first frame as a still poster.
The window moves a fraction of a pixel in each frame, so the motion stays even.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

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
    save_picture,
    work_dir,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

TALL_HEIGHT = 12000
BOTTOM_PAD = 24

THEMES = {
    "report-scroll": "light",
    "report-scroll-dark": "dark",
}

COLOR_FILTER = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
COLOR_TAGS = (
    "-colorspace",
    "bt709",
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
)


def find_ffmpeg() -> str:
    """Return the ffmpeg program, or stop with a hint."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    sys.exit("ffmpeg not found. Run the script inside `nix develop`, or install ffmpeg.")


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


def scroll_tops(
    last: float,
    glide: int,
    hold: int,
) -> list[float]:
    """Return the top of the window for each frame: rest, glide down, rest again."""
    if glide < 2:
        return [0.0] * hold + [last] * hold + [0.0]
    moving = [last * ease(index / (glide - 1)) for index in range(glide)]
    return [0.0] * hold + moving + [last] * hold


def source_view(
    tall: Image.Image,
    width: int,
    view: int,
) -> float:
    """Return how many rows of the tall picture one frame shows."""
    return view * tall.width / width


def with_height(
    tall: Image.Image,
    minimum: float,
) -> Image.Image:
    """Return the picture, padded with its background when it is shorter than one frame."""
    needed = math.ceil(minimum)
    if tall.height >= needed:
        return tall
    padded = Image.new(
        "RGB",
        (tall.width, needed),
        tall.getpixel((4, tall.height - 4)),
    )
    padded.paste(
        tall,
        (0, 0),
    )
    return padded


def render_frame(
    tall: Image.Image,
    top: float,
    width: int,
    view: int,
) -> Image.Image:
    """Return one frame, cut from a fractional row of the tall picture."""
    rows = source_view(
        tall,
        width,
        view,
    )
    top = min(max(top, 0.0), max(tall.height - rows - 1e-6, 0.0))
    return tall.resize(
        (width, view),
        Image.Resampling.LANCZOS,
        box=(0, top, tall.width, top + rows),
    )


def frames_for(
    tall: Image.Image,
    tops: list[float],
    width: int,
    view: int,
) -> Iterator[Image.Image]:
    """Yield the frames, and draw a resting frame only once."""
    previous_top: float | None = None
    previous: Image.Image | None = None
    for top in tops:
        if previous is None or top != previous_top:
            previous = render_frame(
                tall,
                top,
                width,
                view,
            )
            previous_top = top
        yield previous


def ffmpeg_command(
    ffmpeg: str,
    width: int,
    view: int,
    fps: int,
    mp4: Path,
    webm: Path,
) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{view}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-vf",
        COLOR_FILTER,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "27",
        *COLOR_TAGS,
        "-movflags",
        "+faststart",
        str(mp4),
        "-vf",
        COLOR_FILTER,
        "-an",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "40",
        "-row-mt",
        "1",
        *COLOR_TAGS,
        str(webm),
    ]


def encode(
    frames: Iterator[Image.Image],
    command: list[str],
) -> None:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
    )
    assert process.stdin is not None
    try:
        for frame in frames:
            process.stdin.write(frame.convert("RGB").tobytes())
    except BrokenPipeError:
        pass
    finally:
        process.stdin.close()
    if process.wait() != 0:
        sys.exit("ffmpeg failed to write the video.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Make the scrolling videos of the report.")
    parser.add_argument(
        "out",
        type=Path,
        nargs="?",
        default=Path("assets/screenshots"),
        help="folder for the videos and posters",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="width of the video in pixels, an even number",
    )
    parser.add_argument(
        "--view",
        type=int,
        default=720,
        help="height of the video in pixels, an even number",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=22.0,
        help="time the scroll takes from the top to the bottom",
    )
    parser.add_argument(
        "--hold",
        type=float,
        default=1.5,
        help="seconds to rest at the top and at the bottom",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="frames for each second",
    )
    args = parser.parse_args()
    args.out.mkdir(
        parents=True,
        exist_ok=True,
    )

    ffmpeg = find_ffmpeg()
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
            tall = with_height(
                image.crop(
                    (0, 0, WIDTH, min(bottom + BOTTOM_PAD, image.height)),
                ),
                source_view(
                    image,
                    args.width,
                    args.view,
                ),
            )
            rows = source_view(
                tall,
                args.width,
                args.view,
            )
            tops = scroll_tops(
                max(tall.height - rows, 0.0),
                round(args.seconds * args.fps),
                round(args.hold * args.fps),
            )
            mp4 = args.out / f"{name}.mp4"
            webm = args.out / f"{name}.webm"
            encode(
                frames_for(
                    tall,
                    tops,
                    args.width,
                    args.view,
                ),
                ffmpeg_command(
                    ffmpeg,
                    args.width,
                    args.view,
                    args.fps,
                    mp4,
                    webm,
                ),
            )
            save_picture(
                render_frame(
                    tall,
                    0.0,
                    args.width,
                    args.view,
                ),
                args.out / f"{name}.webp",
            )
            print(
                f"{name}  {args.width}x{args.view}  {len(tops)} frames  "
                f"mp4 {mp4.stat().st_size / 1_000_000:.1f} MB  "
                f"webm {webm.stat().st_size / 1_000_000:.1f} MB",
            )
    finally:
        shutil.rmtree(
            folder,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()
