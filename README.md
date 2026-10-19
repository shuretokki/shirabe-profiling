<!--
SPDX-FileCopyrightText: Copyright © 2026 shuretokki
SPDX-License-Identifier: Apache-2.0
-->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/wordmark-on-dark.svg">
    <img src="assets/logo/wordmark-on-light.svg" alt="shirabe" width="240">
  </picture>
</p>

<h1 align="center">shirabe-profiling</h1>

<p align="center">
Polars data profiling that writes one HTML report, with quality alerts and a guide to fix each one.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License: Apache 2.0"></a>
  <a href="https://github.com/shuretokki/shirabe-profiling"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> |
  <a href="#report-tour">Report tour</a> |
  <a href="#use-it-in-code">Use it in code</a> |
  <a href="#license">License</a>
</p>

<p align="center">
  <a href="assets/screenshots/report-overview.webp">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/screenshots/report-overview-dark.webp">
      <img src="assets/screenshots/report-overview.webp" alt="The overview of a report, with the facts of the dataset and the list of alerts" width="880">
    </picture>
  </a>
</p>

shirabe-profiling reads a Polars DataFrame and writes one HTML report that you open in a browser.
The report shows the facts of each column, flags quality problems as alerts, and explains how to fix each alert.

- **Fast,** the engine is Polars, and overview mode skips the slow parts for a quick first look.
- **A guide for every alert,** the Guide tab covers all 10 alerts, with each limit, some possible fixes, and the sources.
- **Made for modeling,** the target section shows how columns link to the target and warns about leakage, and skewed columns get `log1p` and Yeo-Johnson tabs.
- **Easy to use in code,** read the numbers with `.to_dict()`, `.to_json()`, `.stats`, and `.alerts`, and the package is fully typed.
- **Easy on the eyes,** the report follows the theme of your system, and you can switch between dark and light in the settings menu.
- **Open to many inputs,** Polars frames, pandas frames, CSV paths, and Parquet paths all work.

## Quickstart

Install the package from PyPI:

```bash
pip install shirabe-profiling
```

With uv, run `uv add shirabe-profiling` in a project, or `uv pip install shirabe-profiling` in a virtual environment.

For pandas tables with text columns, install the extra: `pip install "shirabe-profiling[pandas]"`.

Then write a report:

```python
import polars as pl
from shirabe_profiling import ProfileReport

df = pl.read_csv("data.csv")
report = ProfileReport(df)
report.to_html("report.html")
```

You can name the column that you want to predict to add a target section:

```python
report = ProfileReport(df, target="price")
```

The report loads ECharts and Tailwind CSS from a CDN, so it needs an internet connection to display correctly.

## Report tour

Click any picture to open it full size.

| Target |
|:--|
| <a href="assets/screenshots/report-target.webp"><img src="assets/screenshots/report-target.webp" alt="Target section with the link of each column to the target" width="100%"></a> |

| Column details |
|:--|
| <a href="assets/screenshots/report-columns.webp"><img src="assets/screenshots/report-columns.webp" alt="Column details with alert tags and skew tabs" width="100%"></a> |

| Correlations |
|:--|
| <a href="assets/screenshots/report-correlations.webp"><img src="assets/screenshots/report-correlations.webp" alt="Correlation heatmap with the strongest pairs" width="100%"></a> |

| Guide |
|:--|
| <a href="assets/screenshots/report-guide.webp"><img src="assets/screenshots/report-guide.webp" alt="The Guide tab with the High Missing alert open" width="100%"></a> |

The report also has:

- A correlation heatmap for each method (Phik, Pearson, Spearman, Cramér's V, and Kendall), with a list of the strongest pairs.
- An Interactions section with scatter plots, box plots, and a column picker.
- A Missing Patterns table and an Outliers table.
- A Sample section with the first rows, the last rows, random rows, and the rows with the most gaps.

## Use it in code

<details>
<summary>Read the results</summary>

```python
report = ProfileReport(df, title="Home Prices Profile")

stats = report.to_dict()
alerts = report.alerts
column_stats = report.stats["area_m2"]
correlations = report.correlations
```

</details>

<details>
<summary>Change the settings</summary>

```python
from shirabe_profiling import ProfileReport, ProfileConfig

config = ProfileConfig(
    title="Home Prices Profile",
    mode="overview",
    missing_threshold=0.1,
    histogram_bins=30,
)
report = ProfileReport(df, config=config)
```

</details>

<details>
<summary>Pick a mode</summary>

Use `"overview"` when you want a fast first look, because it skips the slow parts of the report.

| Feature | `"complete"` | `"overview"` |
|---|:-:|:-:|
| Basic stats | ✓ | ✓ |
| Histograms and value counts | ✓ | ✓ |
| Correlations | ✓ | ✗ |
| Interactions | ✓ | ✗ |
| Skew transform tabs | ✓ | ✗ |
| Missing patterns and outliers tables | ✓ | ✗ |
| Random and most missing samples | ✓ | ✗ |
| Character analysis | ✓ | ✗ |
| Duplicate rows table | ✓ | ✗ |

</details>

<details>
<summary>Choose an output format</summary>

| Format | Method | Use |
|---|---|---|
| HTML | `report.to_html("report.html")` | The interactive report |
| JSON | `report.to_json("report.json")` | Other programs |
| Dict | `report.to_dict()` | Python code |

</details>

## License

This project is a derivative work based on [dataxid-profiling](https://github.com/dataxid/dataxid-profiling) by DataXID, originally licensed under the Apache License 2.0.

- [LICENSE](LICENSE), the Apache-2.0 grant for the whole repository
- [LICENSES/](LICENSES), the full text of each license that the files use
- [REUSE.toml](REUSE.toml), the license and the copyright holder of each file
