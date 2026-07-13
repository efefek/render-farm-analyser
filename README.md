# Render Farm Job Analyser

A command line data processing program that reads a CSV of VFX render farm jobs,
calculates cost and performance metrics for each job, and writes the results to
an output file along with a summary report.

**Module:** CPUF001 Software Foundation — Assessment 1, Development Project
**Author:** Efe Kose
**Python:** 3.10 or newer (standard library only — no packages to install)

---

## The problem

In a VFX studio, render jobs are billed by the hour. A producer needs to know
which shots are consuming the budget *before* the render finishes, not after the
invoice arrives. This program turns a raw job list into per-job costs and
studio-wide statistics so that decision can be made from data rather than
guesswork.

---

## Quick start

### Windows

Double-click `run.bat`, or from a terminal:

```
run.bat                      REM analyses the default file, data\render_jobs.csv
run.bat data\bad_data.csv    REM analyses a file of your choosing
```

### macOS / Linux

```
chmod +x run.sh              # only needed once
./run.sh                     # analyses the default file, data/render_jobs.csv
./run.sh data/bad_data.csv   # analyses a file of your choosing
```

### Running the Python program directly

The data file is passed in as a command line argument. It is never hardcoded, so
the same program works with any correctly formatted CSV:

```
python render_analyser.py data/render_jobs.csv
```

---

## Input format

The program reads **six values** from each row of the input CSV:

| Column | Type | Example | Meaning |
|---|---|---|---|
| `job_id` | text | `J001` | Unique identifier for the job |
| `shot_name` | text | `SH020_explosion` | The VFX shot being rendered |
| `frames` | whole number | `240` | Number of frames in the shot |
| `render_time_per_frame_mins` | decimal | `12.5` | Minutes to render one frame |
| `cost_per_hour` | decimal | `1.40` | Farm rate in GBP per hour |
| `artist` | text | `E.Kose` | Artist the shot is assigned to |

Sample data is provided in `data/render_jobs.csv` (15 jobs).

---

## Calculations

**Per job** (written to `output/results.csv`):

| Metric | Formula |
|---|---|
| Total render time | `frames × render_time_per_frame_mins` |
| Total render hours | `total_render_mins ÷ 60` |
| Total cost | `total_render_hours × cost_per_hour` |
| Cost per frame | `total_cost ÷ frames` |
| Efficiency rating | `Fast` (< 5 min/frame), `Normal`, or `Slow` (> 30 min/frame) |

**Across all jobs** (written to `output/report.txt`):

Total cost · total frames · total render hours · average render time per job ·
average cost per job · most expensive shot · slowest shot · cost broken down by
artist · highest-spending artist.

---

## Output files

Both are created in the `output/` folder, which the program creates if it does
not already exist.

- **`output/results.csv`** — one row per job: the original data plus every
  calculated metric. Opens directly in Excel.
- **`output/report.txt`** — a human-readable report describing the processing
  run: timestamp, input file, rows read, rows processed, **every skipped row with
  the reason it was rejected**, and the summary statistics.

---

## Error handling

The program is designed so that bad data degrades the result rather than
destroying it. A single malformed row is skipped and explained; it never stops
the analysis.

| Situation | What happens |
|---|---|
| No file given on the command line | Usage message printed, exits with code **2** |
| File does not exist | Clear error message, exits with code **1** |
| File has the wrong columns | Reports expected vs. found columns, exits with code **1** |
| File is not readable text | Reports that the file is not a CSV, exits with code **1** |
| Row has too few or too many fields | Row skipped, reason recorded in the report |
| Text where a number belongs (`twelve`) | Row skipped, reason recorded in the report |
| Zero or negative `frames` | Row skipped — this is what prevents a divide-by-zero in the cost-per-frame calculation |
| Zero or negative time or cost | Row skipped, reason recorded in the report |
| Empty field | Row skipped, reason recorded in the report |
| Blank line | Skipped quietly and logged |
| No valid rows at all | Summary statistics are skipped rather than dividing by zero; the report explains why |

### Seeing it work

`data/bad_data.csv` contains twelve rows, deliberately broken in ten different
ways. Run it to see the error handling in action:

```
python render_analyser.py data/bad_data.csv
```

The program processes the 3 valid rows, skips the other 10, and lists each
rejection with its real line number in `output/report.txt`.

---

## Project structure

```
render-farm-analyser/
├── render_analyser.py     The data processing program
├── run.bat                Windows launcher script
├── run.sh                 macOS / Linux launcher script
├── data/
│   ├── render_jobs.csv    Sample data — 15 valid render jobs
│   └── bad_data.csv       Deliberately broken data, for testing error handling
├── output/
│   ├── results.csv        Generated: per-job calculations
│   └── report.txt         Generated: processing report and summary statistics
├── docs/
│   └── flowchart.md       Flowcharts and pseudocode for the Development Document
└── README.md
```

---

## How the code is structured

The program is organised into five sections, each with a single responsibility.
`main()` reads as a plain list of steps, so the shape of the whole program is
visible at a glance while the detail lives in the functions below it.

1. **Command line handling** — `parse_arguments()` reads the file path from
   `sys.argv` and checks the argument count before using it.
2. **Reading and validating** — `read_jobs()`, `validate_header()`, `parse_row()`
   and `to_positive_number()` turn raw text into trustworthy numbers, returning
   both the valid jobs *and* the rejected rows with their reasons.
3. **Calculations** — `calculate_metrics()` and `rate_efficiency()` work out the
   per-job figures; `summarise()` produces the studio-wide statistics.
4. **Writing output** — `write_results_csv()` and `write_report()`.
5. **`main()`** — the sequence that ties it all together.
