# Laboratory Moving Averages

A Streamlit app for exploring laboratory result moving averages by analyte and instrument.

Current working version: `0.2.0`

License: BSD 3-Clause. See [LICENSE](LICENSE).

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the web UI:

```powershell
streamlit run app.py
```

Or run it with the project script:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_streamlit.ps1
```

You can also use the command-file launcher:

```powershell
.\scripts\start_streamlit.cmd
```

The app expects CSV files with these columns:

```csv
date,analyte,instrument,result
2026-01-02 08:14:03.125,Glucose,Architect c8000,96.2
2026-01-02 08:19:48.502,Glucose,Atellica CH,94.8
2026-01-02 08:11:29.411,Creatinine,Architect c8000,0.91
```

Each analyte is shown in its own tab. Inside each tab, choose which instruments to include in the chart. The moving-average slider controls how many recent result points are used.

Visualization modes:

- `Separate instruments`: shows each selected instrument with its own result markers and moving-average line.
- `Combined instruments`: pools the selected instruments in date/time order and shows one combined moving-average line, while still showing the selected instruments' raw result markers.

Charts use a high-contrast color palette designed to remain legible in both light and dark Streamlit themes.

Each moving-average line includes statistical reference lines:

- `mean`: mean of that line's moving-average graph points.
- `+1 SD`: one sample standard deviation above that moving-average mean.
- `-1 SD`: one sample standard deviation below that moving-average mean.
- `+2 SD`: two sample standard deviations above that moving-average mean.
- `-2 SD`: two sample standard deviations below that moving-average mean.

These reference lines are recalculated when the moving-average point count changes.
Use `Show mean and SD reference lines` to show or hide all reference lines for the current analyte with one click. When shown, the reference lines are grouped with their moving-average line in the legend and can still be toggled individually.
Each overview and instrument chart includes a statistics table with the moving-average window size, number of moving-average values, mean, SD, mean +/-1 SD, mean +/-2 SD, and median. The median is shown in the table but is not graphed.
Use `Instrument charts` to show separate charts for each selected instrument. This section is expanded by default and appears before the analyte data table. Each instrument chart has its own mean/SD reference-line checkbox.
Each instrument chart also includes a collapsed `Additional graphs` section with three views: a raw-result time-series chart, an MA-value normal distribution, and a raw-result normal distribution. The raw-result time-series chart includes its own statistics table and mean, +/-1 SD, and +/-2 SD line control. Both distribution charts include a fitted normal curve, fixed 95% cutoff lines, optional custom confidence-level cutoff lines, and side-by-side statistics columns for the fixed and custom intervals. The intervals use `mean +/- z x sample SD`; they describe the fitted distribution rather than the confidence interval of the estimated mean.

Each analyte tab also includes `Axis controls`:

- `Y-axis scale`: use automatic scaling or enter a manual Y minimum and maximum.
- `X-axis range`: use the full date/time range or enter manual start and end timestamps.
- Manual X-axis timestamps use the same format as the CSV date field, for example `2026-01-02 08:14:03.125`.

## CSV Format

A sample file is included at `sample_lab_data.csv`.

Required columns:

| Column | Required format | Notes |
| --- | --- | --- |
| `date` | `YYYY-MM-DD HH:MM:SS.mmm` | Collection date/time, run date/time, or result date/time. Rows are sorted by this value before calculating moving averages. Milliseconds are supported. |
| `analyte` | text | Test/analyte name, such as `Glucose`, `Creatinine`, or `Sodium`. Each analyte gets its own tab. |
| `instrument` | text | Instrument or analyzer name. Each analyte tab lets you choose which instruments to include. |
| `result` | number | Numeric lab result used for the moving-average calculation. |

Formatting rules:

- Keep the column names exactly as shown: `date`, `analyte`, `instrument`, `result`.
- Use a timestamp in the `date` column when available, for example `2026-01-02 08:14:03.125`.
- Date-only values like `2026-01-02` are still accepted, but timestamps are recommended when result order matters within a day.
- Use one row per result.
- Do not include units in the `result` column; keep it numeric.
- Use consistent analyte and instrument names so the app groups rows correctly.
- Blank, invalid, or non-numeric result rows are ignored during cleaning.
