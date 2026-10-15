<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/wordmark-on-dark.svg">
    <img src="assets/logo/wordmark-on-light.svg" alt="shirabe" width="240">
  </picture>
</p>

# shirabe-profiling

[![License](https://img.shields.io/github/license/shuretokki/shirabe-profiling.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)

Fast, Polars-native data profiling with interactive HTML reports and data quality alerts.

## Quickstart

```python
import polars as pl
from shirabe_profiling import ProfileReport

df = pl.read_csv("data.csv")
report = ProfileReport(df)
report.to_html("report.html")
```

Pandas works too:

```python
report = ProfileReport(pd.read_csv("data.csv"))
```

## Report Preview

**Dataset overview** — row and column counts, missing cells, duplicates, memory, the column types, the alerts, and a target section when you pass `target=`.

<p align="center">
  <img src="docs/report-overview.png" alt="Dataset overview and alerts" width="700">
</p>

**Column details** — statistics for each column, a tag for each alert, and a highlight on the statistic that raised it. A skewed column gets tabs that show the data after `log1p` and Yeo-Johnson, each with its own statistics.

<p align="center">
  <img src="docs/report-columns.png" alt="Column details with alert tags and skew tabs" width="700">
</p>

**Correlations** — a heatmap for each method (Phik, Pearson, Spearman, Cramér's V, and Kendall) and a list of the strongest pairs.

<p align="center">
  <img src="docs/report-correlations.png" alt="Correlation heatmap" width="700">
</p>

**Interactions** — scatter plots for numeric pairs and box plots for categorical × numeric pairs, with dynamic column selection.

## Highlights

- Built on Polars: fast, memory-efficient, Rust-powered
- 3 lines to profile any dataset
- Programmatic-first: `.to_dict()`, `.stats`, `.alerts`
- One HTML file with interactive ECharts charts, a dark theme, and a light theme
- A Guide tab that explains each alert, when the report raises it, and how to fix it, with sources
- Accepts Polars, Pandas, CSV, and Parquet
- 5 column types: numeric, categorical, boolean, datetime, and text
- 10 data quality alerts out of the box
- 5 correlation types: Pearson, Spearman, Kendall, Cramér's V, and Phi K
- A target section with a leakage check, when you pass `target=`
- Interactions: scatter plot and box plot with dynamic column selection
- Categorical value counts keep the long tail with an explicit "Other" rollup (`other_values`)
- Two modes: `"complete"` for deep analysis and `"overview"` for speed
- Fully typed

## Installation

The package is not on PyPI yet. Install it from GitHub:

```bash
pip install git+https://github.com/shuretokki/shirabe-profiling.git
```

The report loads ECharts and Tailwind CSS from a CDN, so it needs an internet connection when you open it.

## Usage

### Programmatic access

```python
report = ProfileReport(df, title="Customer Data Profile")

stats = report.to_dict()
alerts = report.alerts
column_stats = report.stats["age"]
correlations = report.correlations
```

### Target

Name the column that you want to predict to get the target section and the leakage check:

```python
report = ProfileReport(df, target="churned")
```

### JSON export

```python
report.to_json("report.json")
```

### Configuration

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

| Feature | `"complete"` | `"overview"` |
|---|:-:|:-:|
| Basic stats | ✓ | ✓ |
| Histograms & value counts | ✓ | ✓ |
| Correlations | ✓ | ✗ |
| Interactions | ✓ | ✗ |
| Skew transform tabs | ✓ | ✗ |
| Missing patterns and outliers tables | ✓ | ✗ |
| Random and most missing samples | ✓ | ✗ |
| Character analysis | ✓ | ✗ |
| Duplicate rows table | ✓ | ✗ |

## Output formats

| Format | Method | Use case |
|---|---|---|
| HTML | `report.to_html("report.html")` | Interactive report |
| JSON | `report.to_json("report.json")` | Machine-readable |
| Dict | `report.to_dict()` | Python-native |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Links

- [Changelog](CHANGELOG.md)
- [GitHub Issues](https://github.com/shuretokki/shirabe-profiling/issues)

## License

[Apache-2.0](LICENSE). The work of others that this project includes or loads is listed in [LICENSES.md](LICENSES.md).

This project began as a copy of [dataxid-profiling](https://github.com/dataxid/dataxid-profiling) by DataXID, which is also Apache-2.0.
