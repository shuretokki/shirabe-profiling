# SPDX-FileCopyrightText: Copyright © 2026 shuretokki
# SPDX-License-Identifier: Apache-2.0

"""Check a built package against the rules that PyPI enforces when you upload it.

The rules come from the upload code of Warehouse (warehouse/forklift/legacy.py and metadata.py).
They are valid and current classifiers, a summary of 512 characters or fewer,
project URL labels of 32 characters or fewer, no local version,
License and License-Expression never together, license files inside the archive,
file names that match the metadata, a RECORD file in a wheel,
no direct URL dependencies, and files of 100 MiB or less.
The script also warns when the README relies on something that PyPI does not show.

Run it with: uv run python scripts/check_package.py dist
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from packaging.metadata import ExceptionGroup, Metadata
from packaging.utils import canonicalize_name, parse_sdist_filename, parse_wheel_filename
from packaging.version import Version
from readme_renderer import markdown
from trove_classifiers import all_classifiers, deprecated_classifiers

MAX_FILE_BYTES = 100 * 1024 * 1024
SUMMARY_LIMIT = 512
LABEL_LIMIT = 32


def read_archive(path: Path) -> tuple[bytes, list[str]]:
    """Return the metadata text and the member names of a wheel or an sdist."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as wheel:
            names = wheel.namelist()
            found = [name for name in names if name.endswith(".dist-info/METADATA")]
            return wheel.read(found[0]) if found else b"", names
    with tarfile.open(path) as sdist:
        names = sdist.getnames()
        found = [name for name in names if name.count("/") == 1 and name.endswith("/PKG-INFO")]
        member = sdist.extractfile(found[0]) if found else None
        return member.read() if member else b"", names


def check_metadata(
    meta: Metadata,
    names: list[str],
    path: Path,
    problems: list[str],
    warnings: list[str],
) -> None:
    summary = meta.summary or ""
    if len(summary) > SUMMARY_LIMIT or "\n" in summary:
        problems.append(f"the summary must be one line of {SUMMARY_LIMIT} characters or fewer")

    for classifier in sorted(set(meta.classifiers or []) - set(all_classifiers)):
        problems.append(f"{classifier!r} is not a valid classifier")
    for classifier in sorted(set(meta.classifiers or []) & set(deprecated_classifiers)):
        use = deprecated_classifiers[classifier]
        problems.append(f"the classifier {classifier!r} is deprecated, use {use or 'none'}")

    for label, url in (meta.project_urls or {}).items():
        if len(label) > LABEL_LIMIT:
            problems.append(
                f"the project URL label {label!r} is longer than {LABEL_LIMIT} characters",
            )
        if urlparse(url).scheme not in {"http", "https"}:
            problems.append(f"the project URL {url!r} is not an http or https link")

    if meta.version.local:
        problems.append(f"the local version in {meta.version} is not allowed on PyPI")

    if meta.license and meta.license_expression:
        problems.append("License and License-Expression must not be used together")
    for license_file in meta.license_files or []:
        if not any(name.endswith(license_file) for name in names):
            problems.append(f"the license file {license_file} is not inside {path.name}")

    for requirement in meta.requires_dist or []:
        if requirement.url is not None:
            problems.append(f"the direct dependency {requirement} is not allowed on PyPI")

    if path.suffix == ".whl":
        if not any(name.endswith(".dist-info/RECORD") for name in names):
            problems.append("the wheel has no RECORD file")
        name, version, _, _ = parse_wheel_filename(path.name)
    else:
        name, version = parse_sdist_filename(path.name)
    if canonicalize_name(meta.name) != name or Version(str(meta.version)) != version:
        problems.append(f"the file name {path.name} does not match {meta.name} {meta.version}")

    if path.stat().st_size > MAX_FILE_BYTES:
        problems.append(f"{path.name} is larger than 100 MiB")

    if meta.description_content_type is None and meta.description:
        warnings.append("the description has no content type, PyPI shows it as plain text")


def check_readme(
    meta: Metadata,
    warnings: list[str],
) -> None:
    text = meta.description or ""
    rendered = markdown.render(text)
    if rendered is None:
        warnings.append("PyPI cannot render the README")
        return
    source_tags = set(
        re.findall(
            r"<([a-z][a-z0-9]*)\b",
            text,
        ),
    )
    kept_tags = set(
        re.findall(
            r"<([a-z][a-z0-9]*)\b",
            rendered,
        ),
    )
    dropped = sorted(source_tags - kept_tags)
    if dropped:
        warnings.append(f"PyPI removes these README tags: {', '.join(dropped)}")
    relative = re.findall(
        r'(?:src="|\]\()((?!https?:|#|mailto:)[^"\s)]+\.(?:png|svg|jpg|gif))',
        text,
    )
    if relative:
        warnings.append(f"PyPI does not show relative images, such as {relative[0]}")


def main() -> int:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    files = sorted([*dist.glob("*.whl"), *dist.glob("*.tar.gz")])
    if not files:
        print(f"no wheel or sdist in {dist}")
        return 1

    failed = False
    shown_readme = False
    for path in files:
        data, names = read_archive(path)
        problems: list[str] = []
        warnings: list[str] = []
        try:
            meta = Metadata.from_email(
                data,
                validate=True,
            )
        except ExceptionGroup as group:
            problems.extend(str(error) for error in group.exceptions)
        else:
            check_metadata(
                meta,
                names,
                path,
                problems,
                warnings,
            )
            if not shown_readme:
                check_readme(
                    meta,
                    warnings,
                )
                shown_readme = True
        print(f"{path.name}: {'FAILED' if problems else 'ok'}")
        for problem in problems:
            print(f"  error: {problem}")
        for warning in warnings:
            print(f"  warning: {warning}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
