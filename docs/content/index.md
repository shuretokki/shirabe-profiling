---
seo:
  title: shirabe-profiling
  description: Profile a Polars table and write one HTML report, with quality alerts and a guide to fix each alert.
---

::u-page-hero
#title
Profile a Polars table and write one HTML report

#description
Pass a Polars DataFrame to get one HTML report with the facts of each column and a list of quality alerts.
Open the Guide tab to see how to fix each alert.

#links
  :::u-button
  ---
  color: neutral
  size: lg
  to: /getting-started/introduction
  trailing-icon: i-lucide-arrow-right
  ---
  Get started
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
  Open the Alerts section to find missing values, constant columns, skewed columns, and high correlations, each with the name of its column.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-book-open
  ---
  #title
  A guide for every alert

  #description
  Open the Guide tab to see the limit of each alert, some possible fixes, and the sources.
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
  Call `to_dict`, `to_json`, `stats`, or `alerts` to read the numbers in code, with type hints for your editor.
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
