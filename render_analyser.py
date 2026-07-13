#!/usr/bin/env python3
"""
render_analyser.py - Render Farm Job Analyser
=============================================

Module : CPUF001 Software Foundation
Author : Efe Kose
Purpose: Reads a CSV file of VFX render farm jobs (passed in as a command line
         argument), calculates cost and performance metrics for each job, and
         writes two output files: a results CSV and a plain-text summary report.

WHY THIS PROBLEM: In a VFX studio, render jobs are billed by the hour. Producers
need to know which shots are burning the budget BEFORE the render finishes, not
after. This program turns a raw job list into per-job costs and studio-wide
statistics so that decision can be made from data.

USAGE:
    python render_analyser.py <input_csv_file>

EXAMPLE:
    python render_analyser.py data/render_jobs.csv

EXIT CODES (so that the calling .bat / .sh script can react to failure):
    0 = success
    1 = a fatal error occurred (e.g. input file could not be read)
    2 = the program was called incorrectly (wrong number of arguments)
"""

import csv
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
# These are named constants rather than "magic numbers" scattered through the
# code. If the studio changes its efficiency thresholds, we edit ONE line here
# instead of hunting through every function.

# The exact column names we require in the input file. The program validates the
# header against this list, so a wrong file (e.g. a shopping list) fails loudly
# and immediately instead of producing nonsense numbers.
EXPECTED_COLUMNS = [
    "job_id",
    "shot_name",
    "frames",
    "render_time_per_frame_mins",
    "cost_per_hour",
    "artist",
]

MINUTES_PER_HOUR = 60          # Used to convert render minutes into billable hours.
FAST_THRESHOLD_MINS = 5.0      # Under 5 min/frame is considered a light render.
SLOW_THRESHOLD_MINS = 30.0     # Over 30 min/frame is a heavy render worth flagging.

OUTPUT_DIR = "output"                              # All generated files live here.
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.csv")
REPORT_FILE = os.path.join(OUTPUT_DIR, "report.txt")


# ---------------------------------------------------------------------------
# 1. COMMAND LINE HANDLING
# ---------------------------------------------------------------------------

def parse_arguments(argv):
    """Return the input file path taken from the command line.

    sys.argv is a list where argv[0] is the script name itself, so a correct
    call gives us exactly 2 items. We check this explicitly rather than just
    indexing argv[1], because indexing a missing item would crash with an
    unfriendly IndexError. Handling it ourselves lets us print a usage message
    the user can actually act on.
    """
    if len(argv) != 2:
        print("ERROR: wrong number of arguments.", file=sys.stderr)
        print(f"Usage: python {os.path.basename(argv[0])} <input_csv_file>",
              file=sys.stderr)
        print("Example: python render_analyser.py data/render_jobs.csv",
              file=sys.stderr)
        sys.exit(2)  # Exit code 2 = usage error, so scripts can tell it apart.

    return argv[1]


# ---------------------------------------------------------------------------
# 2. READING AND VALIDATING THE INPUT DATA
# ---------------------------------------------------------------------------

def validate_header(header, source_path):
    """Confirm the CSV header contains the columns we depend on.

    We compare against EXPECTED_COLUMNS *before* reading any data rows. Failing
    here is deliberate: if the columns are wrong, every row would fail anyway,
    and a single clear message is far more useful than 15 identical row errors.
    """
    if header is None:
        raise ValueError(f"'{source_path}' is empty - no header row found.")

    # Strip whitespace so that "frames " and "frames" are treated as the same.
    cleaned = [column.strip() for column in header]

    if cleaned != EXPECTED_COLUMNS:
        raise ValueError(
            f"'{source_path}' has the wrong columns.\n"
            f"  Expected: {','.join(EXPECTED_COLUMNS)}\n"
            f"  Found   : {','.join(cleaned)}"
        )


def to_positive_number(text, field_name, converter):
    """Convert a string from the CSV into a positive int or float.

    Everything read from a CSV arrives as a string, so "240" must be turned into
    the number 240 before we can do arithmetic on it. Two things can go wrong,
    and we handle both:
      1. The text is not a number at all ("twelve")     -> ValueError from int()/float()
      2. The text IS a number but is zero or negative   -> physically impossible
         for a frame count or a duration, and a zero frame count would later
         cause a divide-by-zero in the cost-per-frame calculation.

    'converter' is passed in as an argument (int for frames, float for times).
    Passing a function as a parameter lets one function serve both cases instead
    of writing two nearly identical ones.
    """
    if text is None or text.strip() == "":
        raise ValueError(f"'{field_name}' is empty")

    try:
        value = converter(text.strip())
    except ValueError:
        # We catch the built-in error and re-raise it with a message that names
        # the offending field, which is what ends up in the report file.
        raise ValueError(f"'{field_name}' is not a valid number (got '{text}')")

    if value <= 0:
        raise ValueError(f"'{field_name}' must be greater than zero (got {value})")

    return value


def parse_row(values, line_number):
    """Turn one raw CSV row (a list of strings) into a validated job dictionary.

    Raises ValueError with a human-readable reason if the row is unusable. The
    caller catches that error, records the reason, and moves on to the next row
    - one bad row must never stop the whole analysis.
    """
    # A row with the wrong number of fields cannot be mapped to our columns.
    # This catches both truncated rows and rows with a stray extra comma.
    if len(values) != len(EXPECTED_COLUMNS):
        raise ValueError(
            f"expected {len(EXPECTED_COLUMNS)} fields but found {len(values)}"
        )

    # zip() pairs each column name with its value, giving us a dictionary we can
    # read by name (row["frames"]) instead of by position (values[2]). Naming
    # things makes the calculations below far easier to read and to get right.
    row = dict(zip(EXPECTED_COLUMNS, values))

    # Text fields just need to be non-empty; numeric fields need full validation.
    job_id = row["job_id"].strip()
    shot_name = row["shot_name"].strip()
    artist = row["artist"].strip()

    if not job_id:
        raise ValueError("'job_id' is empty")
    if not shot_name:
        raise ValueError("'shot_name' is empty")
    if not artist:
        raise ValueError("'artist' is empty")

    return {
        "line_number": line_number,
        "job_id": job_id,
        "shot_name": shot_name,
        "frames": to_positive_number(row["frames"], "frames", int),
        "render_time_per_frame_mins": to_positive_number(
            row["render_time_per_frame_mins"], "render_time_per_frame_mins", float
        ),
        "cost_per_hour": to_positive_number(
            row["cost_per_hour"], "cost_per_hour", float
        ),
        "artist": artist,
    }


def read_jobs(input_path):
    """Read the input CSV and return (valid_jobs, skipped_rows).

    Returns TWO lists rather than one. The skipped rows are not thrown away -
    they are reported at the end, so the user can see exactly which lines were
    rejected and why. Silently dropping data would be worse than crashing.
    """
    jobs = []
    skipped = []

    # A 'with' block guarantees the file is closed even if an error is raised
    # part way through reading it.
    # newline="" is what the csv module documentation requires: it stops Python
    # from mangling line endings inside quoted fields.
    with open(input_path, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)

        # next() pulls the header off the top so the loop below only ever sees
        # data rows. The default None means an empty file does not crash here.
        header = next(reader, None)
        validate_header(header, input_path)

        # ITERATION: one pass over the file, one row at a time. This scales to a
        # 100,000-row farm log because we never hold the whole file in memory.
        for values in reader:
            line_number = reader.line_num  # True line number, useful for the report.

            # SELECTION: skip blank lines quietly. A trailing newline at the end
            # of a file is normal and is not a data error worth reporting.
            if not values or all(field.strip() == "" for field in values):
                skipped.append((line_number, "blank line"))
                continue

            try:
                jobs.append(parse_row(values, line_number))
            except ValueError as error:
                # The row is bad, but the FILE is still fine. Record the reason
                # and keep going - this is the difference between a program that
                # falls over on real-world data and one that survives it.
                skipped.append((line_number, str(error)))

    return jobs, skipped


# ---------------------------------------------------------------------------
# 3. THE CALCULATIONS
# ---------------------------------------------------------------------------

def rate_efficiency(mins_per_frame):
    """Classify a job as Fast / Normal / Slow based on its per-frame time.

    A plain if/elif/else chain: a producer scanning the results CSV wants a word,
    not a number, to tell them where to look first.
    """
    if mins_per_frame < FAST_THRESHOLD_MINS:
        return "Fast"
    elif mins_per_frame > SLOW_THRESHOLD_MINS:
        return "Slow"
    else:
        return "Normal"


def calculate_metrics(job):
    """Perform the per-job calculations and return them merged into the job.

    Four calculations happen here:
      1. total_render_mins  = frames x minutes per frame
      2. total_render_hours = total minutes / 60      (the farm bills by the hour)
      3. total_cost_gbp     = hours x cost per hour
      4. cost_per_frame_gbp = total cost / frames     (lets us compare shots of
                                                       different lengths fairly)
    """
    frames = job["frames"]
    mins_per_frame = job["render_time_per_frame_mins"]

    total_render_mins = frames * mins_per_frame
    total_render_hours = total_render_mins / MINUTES_PER_HOUR
    total_cost_gbp = total_render_hours * job["cost_per_hour"]

    # DIVIDE-BY-ZERO GUARD.
    # parse_row() already rejects a frame count of zero, so in theory this can
    # never trigger. It is kept deliberately: the guard means that if someone
    # later relaxes that validation rule, this calculation degrades to 0.0
    # instead of crashing the whole run on the very last job in the file.
    try:
        cost_per_frame_gbp = total_cost_gbp / frames
    except ZeroDivisionError:
        cost_per_frame_gbp = 0.0

    # Build a NEW dictionary rather than modifying the one we were given. The
    # original parsed data stays untouched, which makes the flow easier to trace.
    return {
        **job,
        "total_render_mins": round(total_render_mins, 2),
        "total_render_hours": round(total_render_hours, 2),
        "total_cost_gbp": round(total_cost_gbp, 2),
        "cost_per_frame_gbp": round(cost_per_frame_gbp, 4),
        "efficiency_rating": rate_efficiency(mins_per_frame),
    }


def summarise(results):
    """Calculate studio-wide statistics across every successfully processed job.

    Returns None when there are no results at all. Returning None instead of
    calculating an average of an empty list is what stops a ZeroDivisionError
    when the input file contains a valid header but no usable rows.
    """
    if not results:
        return None

    total_cost = sum(job["total_cost_gbp"] for job in results)
    total_hours = sum(job["total_render_hours"] for job in results)
    total_frames = sum(job["frames"] for job in results)

    # max() with a key tells Python WHICH field to compare the jobs on, so we get
    # the whole job dictionary back, not just the winning number.
    most_expensive = max(results, key=lambda job: job["total_cost_gbp"])
    slowest = max(results, key=lambda job: job["render_time_per_frame_mins"])

    # Total up the cost per artist by accumulating into a dictionary. If the
    # artist has not been seen before, .get() supplies a starting value of 0.
    cost_by_artist = {}
    for job in results:
        artist = job["artist"]
        cost_by_artist[artist] = cost_by_artist.get(artist, 0) + job["total_cost_gbp"]

    busiest_artist = max(cost_by_artist, key=cost_by_artist.get)

    return {
        "job_count": len(results),
        "total_frames": total_frames,
        "total_cost_gbp": round(total_cost, 2),
        "total_render_hours": round(total_hours, 2),
        "average_render_hours": round(total_hours / len(results), 2),
        "average_cost_gbp": round(total_cost / len(results), 2),
        "most_expensive_shot": most_expensive["shot_name"],
        "most_expensive_cost": most_expensive["total_cost_gbp"],
        "slowest_shot": slowest["shot_name"],
        "slowest_mins_per_frame": slowest["render_time_per_frame_mins"],
        "busiest_artist": busiest_artist,
        "busiest_artist_cost": round(cost_by_artist[busiest_artist], 2),
        "cost_by_artist": cost_by_artist,
    }


# ---------------------------------------------------------------------------
# 4. WRITING THE OUTPUT FILES
# ---------------------------------------------------------------------------

def ensure_output_dir():
    """Create the output folder if it does not exist.

    exist_ok=True means a second run does not fail just because the folder was
    already made by the first run.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_results_csv(results):
    """Write one row per processed job, with the original data plus every metric.

    We keep the source columns alongside the calculated ones so the output file
    stands on its own - a producer can open it in Excel without needing to
    cross-reference the input.
    """
    columns = [
        "job_id", "shot_name", "artist", "frames",
        "render_time_per_frame_mins", "cost_per_hour",
        "total_render_mins", "total_render_hours",
        "total_cost_gbp", "cost_per_frame_gbp", "efficiency_rating",
    ]

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as csv_file:
        # DictWriter maps dictionary keys onto columns, so the header and the
        # rows can never drift out of order.
        writer = csv.DictWriter(csv_file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for job in results:
            writer.writerow(job)


def write_report(input_path, rows_read, results, skipped, summary):
    """Write the human-readable summary report describing the processing run.

    This file exists to answer the question "can I trust these numbers?" - it
    records what was read, what was rejected and why, and when the run happened.
    """
    timestamp = datetime.now().strftime("%d %B %Y at %H:%M:%S")

    with open(REPORT_FILE, "w", encoding="utf-8") as report:
        report.write("=" * 62 + "\n")
        report.write("RENDER FARM JOB ANALYSER - PROCESSING REPORT\n")
        report.write("=" * 62 + "\n\n")

        report.write("RUN DETAILS\n")
        report.write("-" * 62 + "\n")
        report.write(f"Generated      : {timestamp}\n")
        report.write(f"Input file     : {input_path}\n")
        report.write(f"Results file   : {RESULTS_FILE}\n\n")

        report.write("PROCESSING ACTIVITY\n")
        report.write("-" * 62 + "\n")
        report.write(f"Data rows read : {rows_read}\n")
        report.write(f"Rows processed : {len(results)}\n")
        report.write(f"Rows skipped   : {len(skipped)}\n")

        # SELECTION: only print the rejection table if something was actually
        # rejected. A clean run should not be padded with empty headings.
        if skipped:
            report.write("\nSKIPPED ROWS (line number - reason)\n")
            report.write("-" * 62 + "\n")
            for line_number, reason in skipped:
                report.write(f"  Line {line_number:>3} : {reason}\n")

        report.write("\n")

        if summary is None:
            report.write("SUMMARY STATISTICS\n")
            report.write("-" * 62 + "\n")
            report.write("No valid jobs were processed, so no statistics could\n")
            report.write("be calculated. Check the skipped rows listed above.\n")
            return  # Nothing further to write.

        report.write("SUMMARY STATISTICS\n")
        report.write("-" * 62 + "\n")
        report.write(f"Jobs analysed        : {summary['job_count']}\n")
        report.write(f"Total frames         : {summary['total_frames']}\n")
        report.write(f"Total render time    : {summary['total_render_hours']} hours\n")
        report.write(f"Total cost           : £{summary['total_cost_gbp']}\n")
        report.write(f"Average render time  : {summary['average_render_hours']} hours per job\n")
        report.write(f"Average cost         : £{summary['average_cost_gbp']} per job\n\n")

        report.write("KEY FINDINGS\n")
        report.write("-" * 62 + "\n")
        report.write(f"Most expensive shot  : {summary['most_expensive_shot']} "
                     f"(£{summary['most_expensive_cost']})\n")
        report.write(f"Slowest shot         : {summary['slowest_shot']} "
                     f"({summary['slowest_mins_per_frame']} mins per frame)\n")
        report.write(f"Highest spend artist : {summary['busiest_artist']} "
                     f"(£{summary['busiest_artist_cost']})\n\n")

        report.write("COST BY ARTIST\n")
        report.write("-" * 62 + "\n")
        # sorted() with reverse=True puts the biggest spender at the top, which
        # is the order a producer would want to read it in.
        artist_costs = summary["cost_by_artist"].items()
        for artist, cost in sorted(artist_costs, key=lambda pair: pair[1], reverse=True):
            report.write(f"  {artist:<12} £{round(cost, 2)}\n")


# ---------------------------------------------------------------------------
# 5. MAIN - THE SEQUENCE THAT TIES EVERYTHING TOGETHER
# ---------------------------------------------------------------------------

def main():
    """Run the analysis from start to finish.

    Reads as a plain list of steps: get the argument, read the file, calculate,
    write the outputs, report to the screen. All the detail lives in the
    functions above, so the overall shape of the program is visible at a glance.
    """
    input_path = parse_arguments(sys.argv)

    print("Render Farm Job Analyser")
    print("-" * 40)
    print(f"Reading: {input_path}")

    # File handling errors are caught here, at the top level, because there is
    # nothing sensible the program can do to recover from them - the honest
    # response is a clear message and a non-zero exit code.
    try:
        jobs, skipped = read_jobs(input_path)
    except FileNotFoundError:
        print(f"ERROR: the file '{input_path}' does not exist.", file=sys.stderr)
        print("Check the path and try again.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"ERROR: no permission to read '{input_path}'.", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"ERROR: '{input_path}' is not readable as text. "
              "Is it really a CSV file?", file=sys.stderr)
        sys.exit(1)
    except ValueError as error:
        # Raised by validate_header() when the columns are wrong.
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    rows_read = len(jobs) + len(skipped)

    # ITERATION: apply the calculations to every valid job.
    results = [calculate_metrics(job) for job in jobs]

    summary = summarise(results)

    ensure_output_dir()
    write_results_csv(results)
    write_report(input_path, rows_read, results, skipped, summary)

    # Print a short confirmation so the user knows what happened without having
    # to open the files.
    print(f"Rows read     : {rows_read}")
    print(f"Rows processed: {len(results)}")
    print(f"Rows skipped  : {len(skipped)}")

    if summary is not None:
        print(f"Total cost    : £{summary['total_cost_gbp']}")
        print(f"Most expensive: {summary['most_expensive_shot']} "
              f"(£{summary['most_expensive_cost']})")
    else:
        print("WARNING: no valid jobs found - see the report for the reasons.")

    print("-" * 40)
    print(f"Written: {RESULTS_FILE}")
    print(f"Written: {REPORT_FILE}")


# This guard means the code above only runs when the file is executed directly
# (python render_analyser.py ...). If another program ever imports this file to
# reuse its functions, main() will not fire unexpectedly.
if __name__ == "__main__":
    main()
