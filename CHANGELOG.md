<!--
SPDX-FileCopyrightText: Copyright © 2026 shuretokki
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-19

### Added

- `shirabe_profiling.datasets.make_homes`, a seeded sample table of homes for sale, to try the report before you load your own data
- The Infinite Values alert for numeric columns, with the setting `infinite_threshold`
- The Constant Length alert for text columns whose values all have the same length
- A bar chart for a numeric column with exactly two values, such as 0 and 1, in place of the histogram
- The `pandas` extra: `pip install "shirabe-profiling[pandas]"` adds pyarrow, and the error for a pandas table without pyarrow now names it
- A documentation site, with the source in `docs/`, that a release tag deploys to GitHub Pages
- A benchmark of shirabe-profiling, ydata-profiling, and skrub in `benchmarks/`, which the package does not ship

### Changed

- Alerts are sorted by type, then by value from highest to lowest, in `report.alerts` and in the report
- The Guide tab covers 12 alerts and shows only the fixes that a source backs, so the High Zeros, Infinite Values, and Constant Length alerts have no fix yet
- The Guide names no tool, such as scikit-learn, in its advice
- NumPy is now a declared dependency, because the package already imported it

### Fixed

- A column of type Categorical raised an error, and an Enum column was skipped as unsupported. Both are now profiled as categories

## [0.1.0] - 2026-10-17

First release as `shirabe-profiling`. This project is a derivative work based on [dataxid-profiling](https://github.com/dataxid/dataxid-profiling) 0.4.0 (Apache-2.0).

### Changed

- The package is now `shirabe-profiling` and the import is `shirabe_profiling`
- The report has a new design: a dark theme, a light theme, and a compact density for touch screens
- The report has a new favicon
- The report uses the official IBM Plex Sans font files

### Added

- Guide tab: what each alert means, when the report raises it, possible fixes, and sources
- Feedback tab: request a feature, report a problem with a prefilled GitHub issue, and copy the reproduction details
- Skew tabs in Column Details (`log1p`, Yeo-Johnson, and non-zero) with statistics for each version
- Timeline chart for datetime columns
- Alert tags and a highlighted row in Column Details for the statistic that raised the alert
- Random and Most Missing tabs in Sample
- Download buttons for the correlation matrices
- A target section and leakage check when you pass `target=`
- The full text of each license that the package uses, in `LICENSES/`, and a `license` field that lists all of them
