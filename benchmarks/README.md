# Benchmarks

These numbers come from one machine and one run of the script in this folder. Read the method and the limits before you quote them.

This folder is for developers. The package does not ship it, and the source archive holds only the scripts and the results.

## Understanding the method

Each tool runs on each table in a fresh process, and the clock stops when the HTML file is written. The script reports two times for each pair:

- **First run.** The first run in the new process. It is what you see when you profile a table once.
- **Later runs.** The median of five more runs in the same process. It leaves out one-time costs, such as imports and caches.

A tool that takes more than 60 s on the first run gets no later runs. A run stops after 900 s or at 3,000 MB of memory. No run reached either limit.

| Item | Value |
|:---|:---|
| Date | 2026-10-19 |
| Machine | AMD Ryzen 5 5600, 6 cores and 12 threads, 8.1 GB of memory |
| System | Linux 6.6 on WSL2, Python 3.12.3 |
| shirabe-profiling | Development version after 0.1.0, with Polars 1.39.3 |
| fg-data-profiling | 4.20.0, with pandas 2.3.3. This is the package that was `ydata-profiling`. |
| skrub | 0.11.0 `TableReport`, with Polars 2.0.0 |

Each tool gets its own table type: Polars for shirabe-profiling and skrub, and pandas for ydata. Reading the file is not timed.

The tables:

- **Homes.** The `make_homes` table with 11 columns, at 10,000, 100,000, and 1,000,000 rows.
- **Ames.** The Ames Housing table from OpenML (`house_prices`), with 1,460 rows and 81 columns. Many columns are text, and many have missing values. The file marks a missing value with a question mark, and the script reads it as missing.

## Reading the first run

| Table | shirabe complete | shirabe overview | ydata default | ydata minimal | skrub |
|:---|---:|---:|---:|---:|---:|
| Homes, 10,000 rows | 0.8 s | 0.2 s | 7.5 s | 2.9 s | 0.7 s |
| Homes, 100,000 rows | 1.5 s | 0.2 s | 8.2 s | 3.1 s | 0.8 s |
| Homes, 1,000,000 rows | 6.0 s | 1.0 s | 31.4 s | 5.1 s | 1.5 s |
| Ames, 81 columns | 8.2 s | 0.6 s | 96.8 s | 16.6 s | 0.3 s |

## Reading the later runs

| Table | shirabe complete | shirabe overview | ydata default | ydata minimal | skrub |
|:---|---:|---:|---:|---:|---:|
| Homes, 10,000 rows | 0.38 s | 0.18 s | 7.13 s | 2.82 s | 0.60 s |
| Homes, 100,000 rows | 0.95 s | 0.21 s | 7.78 s | 2.94 s | 0.67 s |
| Homes, 1,000,000 rows | 4.34 s | 0.79 s | 26.45 s | 4.34 s | 1.29 s |
| Ames, 81 columns | 5.31 s | 0.58 s | none | 15.49 s | 0.19 s |

## Reading the memory and the file size

Peak memory is the largest resident memory of the process, including the table.

| Table | shirabe complete | shirabe overview | ydata default | ydata minimal | skrub |
|:---|---:|---:|---:|---:|---:|
| Homes, 10,000 rows | 274 MB | 226 MB | 504 MB | 456 MB | 336 MB |
| Homes, 100,000 rows | 621 MB | 289 MB | 703 MB | 570 MB | 350 MB |
| Homes, 1,000,000 rows | 1,496 MB | 984 MB | 2,002 MB | 1,393 MB | 541 MB |
| Ames, 81 columns | 284 MB | 237 MB | 1,524 MB | 521 MB | 295 MB |

The report file grows with the rows in complete mode.

| Table | shirabe complete | shirabe overview | ydata default | ydata minimal | skrub |
|:---|---:|---:|---:|---:|---:|
| Homes, 10,000 rows | 1.0 MB | 0.3 MB | 3.7 MB | 0.9 MB | 0.5 MB |
| Homes, 100,000 rows | 6.4 MB | 0.3 MB | 3.8 MB | 0.9 MB | 0.5 MB |
| Homes, 1,000,000 rows | 6.5 MB | 0.3 MB | 4.2 MB | 0.9 MB | 0.5 MB |
| Ames, 81 columns | 3.4 MB | 0.8 MB | 55.6 MB | 5.7 MB | 1.0 MB |

## Understanding what the numbers show

- On the Homes tables, complete mode is 5 to 9 times faster than ydata default on the first run, and 6 to 19 times faster on later runs. On Ames it is 12 times faster on the first run.
- Against ydata minimal, complete mode is 3.6, 2.1, and 2.0 times faster on the first run at 10,000 rows, 100,000 rows, and Ames. At 1,000,000 rows it is slower on the first run (6.0 s against 5.1 s) and equal on later runs (4.34 s).
- Overview mode takes 1.0 s or less on the Homes tables, and 0.6 s on Ames.
- On Ames, complete mode takes 8.2 s on the first run and 5.3 s on later runs. The first run in a process carries about 3 s of one-time work.

## Understanding the limits

- One machine and one date. Another CPU or system gives other times.
- The tools do different work. skrub is the fastest here, but I did not check which parts of the analysis it skips, so read its numbers as a reference and not as a like-for-like comparison.
- ydata minimal turns off its slow parts, and shirabe overview does the same. Compare complete with default, and overview with minimal.
- The Homes tables are synthetic. They have few columns and little text, so they show how the time grows with the rows and say little about wide tables.
- A categorical column with hundreds of levels makes complete mode slow, because the Phi K step needs a conversion curve for each table shape. A numeric column that was read as text can cause this.
- The Ames table comes from OpenML, which lists no license for it. The script downloads it to `benchmarks/data/` and does not copy it into the repository.

## Running the benchmark

Run it from the repository root. The first run downloads the Ames table and installs ydata and skrub in isolated environments.

```bash
uv run python benchmarks/run.py
```

Pass `--tables` and `--tools` to run a part, and `--runs`, `--timeout`, and `--memory-mb` to change the limits. A run of one part replaces only its own rows in `results.json`. The script writes `results.json` with the hardware, the commit, and the versions next to every number.
