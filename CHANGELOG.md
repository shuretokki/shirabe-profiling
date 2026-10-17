<!--
SPDX-FileCopyrightText: Copyright © 2026 shuretokki
SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
