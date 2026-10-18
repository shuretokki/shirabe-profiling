# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Make the screenshots for the README.

The script builds a report from the sample table of `make_homes`.
It shows one view at a time in a headless browser and cuts each picture to one fixed size.
Every picture is 1280 by 853 pixels (3:2), so the pictures in the README tables line up.
A light and a dark overview exist, because the README swaps them with the theme of the reader.

It needs Chrome, Chromium, or Edge. Set BROWSER to the program if the script cannot find it.
The report loads ECharts and Tailwind from a CDN, so the script also needs an internet connection.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

from shirabe_profiling import ProfileReport
from shirabe_profiling.datasets import make_homes

WIDTH = 1280
VIEW_HEIGHT = 1100
HEIGHT = 853

BROWSERS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "msedge",
)
WSL_EDGE = Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")

BASE_CSS = "main{padding-top:1.5rem !important}"


def only(*ids: str) -> str:
    """Return CSS that shows only the given sections of the report page."""
    shown = ",".join(f"#page-report>section#{name}" for name in ids)
    return f"#page-report>section{{display:none}}{shown}{{display:block}}"


GUIDE_CSS = (
    "#page-report{display:none}#page-guide[hidden]{display:block !important}"
    "#page-guide>section:not(#guide-alerts){display:none}"
    "#guide-alerts details:nth-of-type(n+4){display:none}"
)


@dataclass(frozen=True)
class Shot:
    name: str
    theme: str
    css: str
    open_first_alert: bool = False
    tab: str = "report"


SHOTS = (
    Shot(
        "report-overview",
        "light",
        only(
            "overview-section",
            "alerts-section",
        ),
    ),
    Shot(
        "report-target",
        "light",
        only("target-section"),
    ),
    Shot(
        "report-columns",
        "light",
        only("columns-section"),
    ),
    Shot(
        "report-correlations",
        "light",
        only("correlations-section") + ".pair-list li:nth-child(n+6){display:none}",
    ),
    Shot(
        "report-guide",
        "light",
        GUIDE_CSS,
        open_first_alert=True,
        tab="guide",
    ),
    Shot(
        "report-overview-dark",
        "dark",
        only(
            "overview-section",
            "alerts-section",
        ),
    ),
)


def find_browser() -> str:
    """Return the browser program, from BROWSER, the PATH, or Edge under WSL."""
    chosen = os.environ.get("BROWSER")
    if chosen:
        return chosen
    for name in BROWSERS:
        found = shutil.which(name)
        if found:
            return found
    if WSL_EDGE.exists():
        return str(WSL_EDGE)
    sys.exit("No browser found. Install Chrome, Chromium, or Edge, or set BROWSER.")


def is_windows_program(browser: str) -> bool:
    return browser.lower().endswith(".exe")


def work_dir(browser: str) -> Path:
    """Return a folder that the browser can read, which is a Windows folder for a .exe browser."""
    if not is_windows_program(browser):
        return Path(tempfile.mkdtemp(prefix="shirabe-shots-"))
    raw = subprocess.run(
        ["cmd.exe", "/c", "echo %TEMP%"],
        capture_output=True,
        text=True,
        check=True,
        cwd="/mnt/c",
    ).stdout.strip()
    base = subprocess.run(
        ["wslpath", "-u", raw],
        capture_output=True,
        text=True,
        check=True,
    )
    folder = Path(base.stdout.strip()) / "shirabe-shots"
    folder.mkdir(exist_ok=True)
    return folder


def browser_path(
    browser: str,
    path: Path,
) -> str:
    """Return the path in the form that the browser expects."""
    if not is_windows_program(browser):
        return str(path)
    done = subprocess.run(
        ["wslpath", "-w", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def page_for(
    html: str,
    shot: Shot,
) -> str:
    """Return the report page with the theme and the view for one picture."""
    theme = (
        f"<script>try{{localStorage.setItem('report-theme','{shot.theme}')}}catch(e){{}}</script>"
    )
    style = f"<style>{BASE_CSS}{shot.css}</style>"
    page = html.replace(
        "<script>",
        theme + "<script>",
        1,
    ).replace(
        "</head>",
        style + "</head>",
        1,
    )
    if shot.tab == "guide":
        page = page.replace(
            'id="tab-page-report" aria-controls="page-report" aria-selected="true"',
            'id="tab-page-report" aria-controls="page-report" aria-selected="false"',
            1,
        ).replace(
            'id="tab-page-guide" aria-controls="page-guide" aria-selected="false"',
            'id="tab-page-guide" aria-controls="page-guide" aria-selected="true"',
            1,
        )
    if shot.open_first_alert:
        start = page.index('id="guide-alerts"')
        page = page[:start] + page[start:].replace(
            "<details",
            "<details open",
            1,
        )
    return page


def capture(
    browser: str,
    page: Path,
    png: Path,
) -> None:
    command = [
        browser,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={WIDTH},{VIEW_HEIGHT}",
        "--virtual-time-budget=9000",
        f"--screenshot={browser_path(browser, png)}",
        "file:///"
        + browser_path(
            browser,
            page,
        )
        .replace(
            "\\",
            "/",
        )
        .lstrip("/"),
    ]
    subprocess.run(
        command,
        capture_output=True,
        check=False,
        timeout=180,
    )
    if not png.exists():
        sys.exit(f"The browser made no picture for {page.name}.")


def crop(
    png: Path,
    target: Path,
) -> tuple[int, int]:
    """Cut the picture to one fixed size, so that every picture in the README table matches."""
    image = Image.open(png).convert("RGB")
    background = image.getpixel((4, image.height - 4))
    box = ImageChops.difference(
        image,
        Image.new(
            "RGB",
            image.size,
            background,
        ),
    ).getbbox()
    bottom = box[3] if box else image.height
    if bottom > HEIGHT:
        print(f"  warning: the content of {target.name} is cut at {HEIGHT} pixels")
    canvas = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        background,
    )
    canvas.paste(
        image.crop((0, 0, WIDTH, min(HEIGHT, image.height))),
        (0, 0),
    )
    canvas.save(
        target,
        optimize=True,
    )
    return canvas.size


def main() -> None:
    parser = argparse.ArgumentParser(description="Make the README screenshots.")
    parser.add_argument(
        "out",
        type=Path,
        nargs="?",
        default=Path("docs"),
        help="folder for the pictures",
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
        for shot in SHOTS:
            page = folder / f"{shot.name}.html"
            raw = folder / f"{shot.name}.png"
            page.write_text(
                page_for(
                    html,
                    shot,
                ),
                encoding="utf-8",
            )
            raw.unlink(missing_ok=True)
            capture(
                browser,
                page,
                raw,
            )
            width, height = crop(
                raw,
                args.out / f"{shot.name}.png",
            )
            print(f"{shot.name}.png  {width}x{height}  ({width / height:.2f}:1)")
    finally:
        shutil.rmtree(
            folder,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()
