@echo off
REM ===========================================================================
REM  run.bat - Windows launcher for the Render Farm Job Analyser
REM  Module: CPUF001 Software Foundation
REM
REM  PURPOSE: Runs render_analyser.py from the Command Line Interface and hands
REM  it a data file as an argument. This is the script deliverable required by
REM  the brief - the marker can run the whole program by double-clicking this
REM  file or typing "run.bat" in a terminal.
REM
REM  USAGE:
REM    run.bat                      -> analyses the default file (data\render_jobs.csv)
REM    run.bat data\bad_data.csv    -> analyses a file of your choosing
REM ===========================================================================

REM "@echo off" above stops the console printing every command as it runs, so
REM the user sees only the program's own output. Every line starting with REM is
REM a comment and is ignored by Windows.

REM Move to the folder this script lives in. %~dp0 expands to that folder's full
REM path. WHY: without this, double-clicking the .bat from Explorer could leave
REM the working directory somewhere else, and the relative path "data\..." would
REM not resolve. This makes the script work no matter where it is launched from.
cd /d "%~dp0"

REM ---------------------------------------------------------------------------
REM Choose the data file.
REM %1 is the first argument the user typed after "run.bat". If they did not
REM supply one, %1 is empty, so we fall back to the sample data file. Quoting
REM "%~1" protects against paths that contain spaces.
REM ---------------------------------------------------------------------------
set "DATA_FILE=%~1"
if "%DATA_FILE%"=="" set "DATA_FILE=data\render_jobs.csv"

echo ==========================================
echo  Render Farm Job Analyser
echo  Data file: %DATA_FILE%
echo ==========================================
echo.

REM ---------------------------------------------------------------------------
REM Check the data file exists BEFORE launching Python. The Python program can
REM handle a missing file on its own, but failing here gives a faster, clearer
REM message and demonstrates error checking in the script itself.
REM ---------------------------------------------------------------------------
if not exist "%DATA_FILE%" (
    echo ERROR: the data file "%DATA_FILE%" was not found.
    echo Check the path and try again.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM Run the Python program, passing the data file in as a command line argument.
REM This single line is the heart of the script: it is exactly the command a
REM user would otherwise have to type by hand.
REM ---------------------------------------------------------------------------
python render_analyser.py "%DATA_FILE%"

REM ---------------------------------------------------------------------------
REM ERRORLEVEL holds the exit code the Python program returned. Reading it lets
REM the script report success or failure instead of ending silently:
REM   0 = success, 1 = fatal error, 2 = wrong arguments
REM ---------------------------------------------------------------------------
if %ERRORLEVEL% neq 0 (
    echo.
    echo The analyser reported a problem ^(exit code %ERRORLEVEL%^).
) else (
    echo.
    echo Done. Results are in the "output" folder.
)

REM "pause" holds the window open so that a user who double-clicked this file in
REM Explorer can actually read the output before the console closes.
pause
