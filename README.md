<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/assets/logo/wordmark-on-dark.svg">
    <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/assets/logo/wordmark-on-light.svg" alt="shirabe" width="240">
  </picture>
</p>

<h1 align="center">shirabe-profiling</h1>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/shuretokki/shirabe-profiling.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.10%2B-red.svg" alt="Python 3.10+">
</p>

<p align="center">
High-performance Polars data profiling with web reports and quality warnings.
</p>

## Quickstart

```python
import polars as pl
from shirabe_profiling import ProfileReport

df = pl.read_csv("data.csv")
report = ProfileReport(df)
report.to_html("report.html")
```

Pandas frames, CSV paths, and Parquet paths work too, and you can name the column that you want to predict to add a target section:

```python
report = ProfileReport(df, target="churned")
```

## Highlights

- **Fast,** the engine is Polars, and a complete report for the Kaggle House Prices file (1,460 rows, 81 columns) took 8 to 11 seconds. Overview mode took about 1 second, in single runs on one machine.
- **A guide for every alert,** the Guide tab covers all 10 alerts, with each limit, some possible fixes, and the sources.
- **Made for modeling,** the target section shows how columns link to the target and warns about leakage, and skewed columns get `log1p` and Yeo-Johnson tabs.
- **Easy to use in code,** read the numbers with `.to_dict()`, `.to_json()`, `.stats`, and `.alerts`, and the package is fully typed.

## What the report shows

**Overview,** row and column counts, missing cells, duplicate rows, memory, the column types, and the alerts.

<p align="center">
  <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/docs/report-overview.png" alt="Dataset overview and alerts" width="700">
</p>

**Target,** how each column links to the target, how the target changes across a column, and how missing values relate to the target.

<p align="center">
  <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/docs/report-target.png" alt="Target section with the link of each column to the target" width="700">
</p>

**Column details,** statistics for each column, a tag and a mark for each alert, and tabs for `log1p` and Yeo-Johnson on a skewed column.

<p align="center">
  <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/docs/report-columns.png" alt="Column details with alert tags and skew tabs" width="700">
</p>

**Correlations,** a heatmap for each method (Phik, Pearson, Spearman, Cramér's V, and Kendall), and a list of the strongest pairs.

<p align="center">
  <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/docs/report-correlations.png" alt="Correlation heatmap with the strongest pairs" width="700">
</p>

**Guide,** an alert marks a possible problem, so open it in the Guide tab to see its limit, some possible fixes, and the sources.

<p align="center">
  <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/docs/report-guide.png" alt="The Guide tab with the High Missing alert open" width="700">
</p>

**Dark theme,** the theme follows your system, and you can pick dark or light in the settings menu.

<p align="center">
  <img src="https://raw.githubusercontent.com/shuretokki/shirabe-profiling/main/docs/report-dark.png" alt="Column details in the dark theme" width="700">
</p>

The report also has:

- An Interactions section with scatter plots, box plots, and a column picker.
- A Missing Patterns table and an Outliers table.
- A Sample section with the first rows, the last rows, random rows, and the rows with the most gaps.

## Installation

The package is not on PyPI yet, so install it from GitHub:

```bash
pip install git+https://github.com/shuretokki/shirabe-profiling.git
```

## Usage

### Read the results in code

```python
report = ProfileReport(df, title="Customer Data Profile")

stats = report.to_dict()
alerts = report.alerts
column_stats = report.stats["age"]
correlations = report.correlations
```

### Settings

```python
from shirabe_profiling import ProfileReport, ProfileConfig

config = ProfileConfig(
    title="Customer Data Profile",
    mode="overview",
    missing_threshold=0.1,
    histogram_bins=30,
)
report = ProfileReport(df, config=config)
```

### Modes

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

### Output formats

| Format | Method | Use |
|---|---|---|
| HTML | `report.to_html("report.html")` | The interactive report |
| JSON | `report.to_json("report.json")` | Other programs |
| Dict | `report.to_dict()` | Python code |

## License

[Apache-2.0](LICENSE), and the work of others that this project includes or loads is listed in [LICENSES.md](LICENSES.md).

This project is a derivative work based on [dataxid-profiling](https://github.com/dataxid/dataxid-profiling) by DataXID, originally licensed under the Apache License 2.0.
