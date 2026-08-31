# Solution Design - Flowcharts

These diagrams document the logical operations of the program and its launcher
script, as required by the Solution Design section of the brief.

To produce an image for the Development Document, paste the code block below
into <https://mermaid.live> and export it as a PNG.

---

## Figure 1 - The launcher script (run.bat / run.sh)

The script's only job is to work out *which* data file to analyse, check it is
really there, and then hand it to the Python program as a command line argument.

```mermaid
flowchart TD
    A([Script starts]) --> B[Change to the script's own folder]
    B --> C{Did the user supply<br/>a file name?}
    C -->|Yes| D[Use the supplied file]
    C -->|No| E[Use the default:<br/>data/render_jobs.csv]
    D --> F{Does that file<br/>exist?}
    E --> F
    F -->|No| G[Print error message] --> H([Exit with code 1])
    F -->|Yes| I[Run: python render_analyser.py FILE]
    I --> J{Exit code = 0?}
    J -->|No| K[Report the problem] --> L([End])
    J -->|Yes| M[Print 'Done - see output folder'] --> L
```

Exported PNG: `figure1_launcher.png`

---

## Figure 2 - The Python program (render_analyser.py)

```mermaid
flowchart TD
    A([Program starts]) --> B{Exactly one argument<br/>on the command line?}
    B -->|No| C[Print usage message] --> D([Exit code 2])
    B -->|Yes| E[input_path = sys.argv 1]

    E --> F[Open the input file]
    F --> G{File opened<br/>successfully?}
    G -->|No| H[Print file error] --> I([Exit code 1])

    G -->|Yes| J[Read the header row]
    J --> K{Header matches the<br/>6 expected columns?}
    K -->|No| L[Print column error] --> I

    K -->|Yes| M[/Read the next data row/]
    M --> N{Any rows left?}
    N -->|Yes| O{Is the row valid?<br/>field count, numbers,<br/>positive values}
    O -->|No| P[Add to 'skipped' list<br/>with the reason] --> M
    O -->|Yes| Q[Add to 'jobs' list] --> M

    N -->|No| R[For each valid job, calculate:<br/>total render time<br/>total render hours<br/>total cost<br/>cost per frame<br/>efficiency rating]

    R --> S{Any valid jobs<br/>at all?}
    S -->|Yes| T[Calculate summary statistics:<br/>total cost, averages,<br/>most expensive shot,<br/>cost per artist]
    S -->|No| U[summary = None<br/>avoids dividing by zero]

    T --> V[Write output/results.csv]
    U --> V
    V --> W[Write output/report.txt<br/>including every skipped row<br/>and its reason]
    W --> X[Print a summary to the screen]
    X --> Y([Exit code 0])
```

Exported PNG: `figure2_program.png`

---

## Figure 3 - Row validation, in detail

This is the decision logic inside `parse_row()` and `to_positive_number()`. It is
the part of the program that decides whether a row is trustworthy, and it is
where every one of the deliberate errors in `data/bad_data.csv` gets caught.

```mermaid
flowchart TD
    A([One raw row of text]) --> B{Does it have exactly<br/>6 fields?}
    B -->|No| R[REJECT:<br/>'expected 6 fields but found N']

    B -->|Yes| C{Are job_id, shot_name<br/>and artist all non-empty?}
    C -->|No| S[REJECT:<br/>'field is empty']

    C -->|Yes| D[For each numeric field:<br/>frames, time per frame, cost per hour]
    D --> E{Is the text empty?}
    E -->|Yes| S

    E -->|No| F{Can the text be<br/>converted to a number?}
    F -->|No| T[REJECT:<br/>'not a valid number, got twelve']

    F -->|Yes| G{Is the number<br/>greater than zero?}
    G -->|No| U[REJECT:<br/>'must be greater than zero'<br/>this is what stops a<br/>divide-by-zero later]

    G -->|Yes| V([ACCEPT:<br/>return the job as a dictionary])

    R --> W([Record the reason,<br/>skip the row,<br/>carry on with the next one])
    S --> W
    T --> W
    U --> W
```

Exported PNG: `figure3_validation.png`

---

## Pseudocode (ILO 2)

```
BEGIN
    IF number of command line arguments is not 1 THEN
        print usage message
        exit with code 2
    END IF

    input_file = the command line argument

    TRY
        open input_file
    CATCH file cannot be opened
        print error
        exit with code 1
    END TRY

    read the header row
    IF header does not match the expected columns THEN
        print error
        exit with code 1
    END IF

    jobs    = empty list
    skipped = empty list

    FOR EACH row IN the file
        IF the row is valid THEN
            add it to jobs
        ELSE
            add (line number, reason) to skipped
        END IF
    END FOR

    results = empty list
    FOR EACH job IN jobs
        total_mins  = frames * render_time_per_frame
        total_hours = total_mins / 60
        total_cost  = total_hours * cost_per_hour
        cost_per_frame = total_cost / frames
        rating = Fast, Normal or Slow, depending on time per frame
        add all of these to results
    END FOR

    IF results is empty THEN
        summary = nothing        // avoids dividing by zero
    ELSE
        summary = totals, averages, most expensive shot, cost per artist
    END IF

    write results to output/results.csv
    write summary and skipped rows to output/report.txt
    print a short confirmation to the screen
    exit with code 0
END
```
