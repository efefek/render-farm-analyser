# Render Farm Job Analyser

A command line data processing program that reads a CSV of VFX render farm jobs,
calculates cost and performance metrics for each job, and writes the results to
an output file along with a summary report. It also provides an interactive
project menu when it is launched without a file argument.

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

The packaged Windows executable can use either interface:

```
dist\render-farm-analyser.exe data\render_jobs.csv
dist\render-farm-analyser.exe                         REM opens the project menu
```

### macOS / Linux

```
chmod +x run.sh              # only needed once
./run.sh                     # analyses the default file, data/render_jobs.csv
./run.sh data/bad_data.csv   # analyses a file of your choosing
```

### Running the Python program directly

The **primary interface** passes the data file as a command line argument. This
behaviour is required by the assessment brief and remains the normal way to run
the program, so it works with any correctly formatted CSV without showing a
menu:

```
python render_analyser.py data/render_jobs.csv
```

When no argument is supplied, the fallback interactive menu offers the three
sample projects, a manual CSV path option and a clean quit option:

```
python render_analyser.py
```

Invalid or empty choices are rejected and re-prompted. `Ctrl+C` and end-of-file
input exit cleanly without a traceback.

---

## Sample projects

All three files use the same six-column input format, but represent different
production patterns so their reports tell meaningfully different stories:

| Menu | Project | File | Production profile |
|---|---|---|---|
| 1 | Lighthouse | `data/project1_lighthouse.csv` | A healthy small commercial: short shots, inexpensive nodes and no extreme cost outlier |
| 2 | Northbridge | `data/project2_northbridge.csv` | A simulation-heavy feature film where bridge and flood shots dominate the budget |
| 3 | Kestrel | `data/project3_kestrel.csv` | Episodic TV with many modest jobs spread across a larger artist team |

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

The original sample data remains available in `data/render_jobs.csv` (15 jobs).

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

Output files are created in the `output/` folder, which the program creates if
it does not already exist.

- **`output/results.csv`** — one row per job: the original data plus every
  calculated metric. Opens directly in Excel.
- **`output/report.txt`** — a human-readable report describing the processing
  run: timestamp, input file, rows read, rows processed, **every skipped row with
  the reason it was rejected**, and the summary statistics.

The original `render_jobs.csv` names remain `results.csv` and `report.txt`, and
`bad_data.csv` continues to write `results.csv` and `report_bad_data.txt`.
Other inputs are named from the source file stem, allowing all three project
reports to remain side by side, for example:

- `output/project2_northbridge_results.csv`
- `output/project2_northbridge_report.txt`

---

## Error handling

The program is designed so that bad data degrades the result rather than
destroying it. A single malformed row is skipped and explained; it never stops
the analysis.

| Situation | What happens |
|---|---|
| No file given on the command line | Interactive project-selection menu opens |
| Invalid or empty menu choice | Clear message and another prompt |
| `Ctrl+C`, `Ctrl+Z` or EOF in the menu | Short cancellation message, exits with code **0** |
| Too many command line arguments | Usage message printed, exits with code **2** |
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
│   ├── bad_data.csv       Deliberately broken data, for testing error handling
│   ├── project1_lighthouse.csv   Healthy commercial — 16 valid jobs
│   ├── project2_northbridge.csv  Simulation-heavy feature — 18 valid jobs
│   └── project3_kestrel.csv      Episodic TV — 20 valid jobs
├── output/
│   ├── results.csv        Generated: per-job calculations
│   ├── report.txt         Generated: original sample summary report
│   └── project*_*.{csv,txt}      Generated: separate project outputs
├── docs/
│   └── flowchart.md       Flowcharts and pseudocode for the Development Document
└── README.md
```

---

## How the code is structured

The program is organised into five sections, each with a single responsibility.
`main()` reads as a plain list of steps, so the shape of the whole program is
visible at a glance while the detail lives in the functions below it.

1. **Input selection** — `parse_arguments()` keeps the required command line
   path as the primary route; `choose_input_file()` is the no-argument fallback.
2. **Reading and validating** — `read_jobs()`, `validate_header()`, `parse_row()`
   and `to_positive_number()` turn raw text into trustworthy numbers, returning
   both the valid jobs *and* the rejected rows with their reasons.
3. **Calculations** — `calculate_metrics()` and `rate_efficiency()` work out the
   per-job figures; `summarise()` produces the studio-wide statistics.
4. **Writing output** — `get_output_paths()`, `write_results_csv()` and
   `write_report()` preserve legacy names and create per-project names.
5. **Analysis and entry point** — `analyse_file()` is shared by both interfaces;
   `main()` decides which input-selection route supplies its path.
