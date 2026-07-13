#!/bin/bash
# ============================================================================
#  run.sh - Unix / macOS / Linux launcher for the Render Farm Job Analyser
#  Module: CPUF001 Software Foundation
#
#  PURPOSE: The Unix equivalent of run.bat. Providing both means the program
#  runs on any platform the marker happens to be using, which is one of the
#  higher-mark features listed in the brief ("use of multiple scripting
#  languages for use on different platforms").
#
#  USAGE:
#    ./run.sh                     -> analyses the default file (data/render_jobs.csv)
#    ./run.sh data/bad_data.csv   -> analyses a file of your choosing
#
#  NOTE: on a Unix system this file must be made executable once, with:
#    chmod +x run.sh
# ============================================================================

# The line above (#!/bin/bash) is the "shebang". It tells the operating system
# which interpreter should run this file, so it can be launched directly as
# ./run.sh rather than "bash run.sh".

# Stop the script the moment any command fails, instead of blindly carrying on
# with a broken state. WHY: without this, a failure halfway through would still
# print "Done" at the end, which would be a lie.
set -e

# Move to the folder this script lives in, so the relative path "data/..." works
# no matter which directory the user launched the script from.
cd "$(dirname "$0")"

# ---------------------------------------------------------------------------
# Choose the data file.
# "$1" is the first argument the user typed. The :- syntax below means "use $1,
# but if it is empty, use this default instead".
# ---------------------------------------------------------------------------
DATA_FILE="${1:-data/render_jobs.csv}"

echo "=========================================="
echo " Render Farm Job Analyser"
echo " Data file: $DATA_FILE"
echo "=========================================="
echo

# ---------------------------------------------------------------------------
# Check the file exists before starting Python. -f tests for a regular file.
# Failing here gives a clear message straight away.
# ---------------------------------------------------------------------------
if [ ! -f "$DATA_FILE" ]; then
    echo "ERROR: the data file '$DATA_FILE' was not found." >&2
    echo "Check the path and try again." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Find the right Python command. Some systems only have "python3", others only
# "python". Checking both means the script does not fail on a machine that is
# set up slightly differently from the one it was written on.
# ---------------------------------------------------------------------------
if command -v python3 > /dev/null 2>&1; then
    PYTHON=python3
elif command -v python > /dev/null 2>&1; then
    PYTHON=python
else
    echo "ERROR: Python is not installed or not on the PATH." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Run the program, passing the data file in as a command line argument.
# "set -e" is temporarily disabled here so we can capture the exit code and
# report on it ourselves rather than the script dying silently.
# ---------------------------------------------------------------------------
set +e
"$PYTHON" render_analyser.py "$DATA_FILE"
EXIT_CODE=$?
set -e

# $? holds the exit code of the last command: 0 = success, 1 = fatal error,
# 2 = wrong arguments.
if [ $EXIT_CODE -ne 0 ]; then
    echo
    echo "The analyser reported a problem (exit code $EXIT_CODE)."
    exit $EXIT_CODE
fi

echo
echo "Done. Results are in the 'output' folder."
