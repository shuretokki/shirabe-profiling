---
seo:
  title: shirabe-profiling
  description: Profile a Polars table and write one HTML report, with quality alerts and a guide to fix each alert.
---

::u-page-hero
#title
Profile a Polars table and write one HTML report

#description
shirabe-profiling reads a Polars DataFrame and writes one HTML report.
In the report, you see the facts of each column and a list of quality alerts, and the Guide tab shows how to fix each alert.

#links
  :::u-button
  ---
  color: primary
  size: lg
  to: /tutorials/create-your-first-report
  trailing-icon: i-lucide-arrow-right
  ---
  Create your first report
  :::

  :::u-button
  ---
  color: neutral
  icon: i-simple-icons-github
  size: lg
  to: https://github.com/shuretokki/shirabe-profiling
  variant: outline
  ---
  View on GitHub
  :::

#body
```python
import polars as pl
from shirabe_profiling import ProfileReport

df = pl.read_csv("data.csv")
ProfileReport(df).to_html("report.html")
```

:u-color-mode-image{light="/images/report-overview.png" dark="/images/report-overview-dark.png" alt="The overview of a report, with the facts of a table and the list of alerts" class="mt-6 rounded-md border border-default"}
::

::u-page-section
#title
What the report gives you

#features
  :::u-page-feature
  ---
  icon: i-lucide-triangle-alert
  ---
  #title
  Quality alerts

  #description
  Find missing values, constant columns, skewed columns, high correlations, and more. Each alert names the column that has the problem.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-book-open
  ---
  #title
  A guide for every alert

  #description
  The Guide tab gives the limit of each alert, some possible fixes, and the sources.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-target
  ---
  #title
  Made for modeling

  #description
  Name the target to see how each column links to it and to get a warning about leakage. Skewed columns get transform tabs.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-braces
  ---
  #title
  Results in code

  #description
  Read the numbers with `to_dict`, `to_json`, `stats`, and `alerts`. The package has type hints.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-file-input
  ---
  #title
  Many inputs

  #description
  Pass a Polars DataFrame or LazyFrame, a pandas DataFrame, or the path of a CSV, TSV, or Parquet file.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-sun-moon
  ---
  #title
  Dark and light themes

  #description
  Switch between dark and light in the settings menu, or let the report follow the theme of your system.
  :::
::
