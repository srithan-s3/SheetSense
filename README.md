# SheetSense

**Turn Your Spreadsheets Into Insights.** A working, local-first Excel/CSV analytics
application built for a Web Programming mini-project. React renders analysis
returned by Flask and Pandas; uploaded files and sample files use the same pipeline.
Core functionality requires no account, paid service, API key, or external AI.

## What you can do

- Upload `.csv`, `.xlsx`, or legacy `.xls` files and choose an Excel worksheet.
- Inspect paginated records, search records on the server, and review inferred types.
- Generate dataset-specific metrics, suitable charts, statistical observations,
  and data quality findings from actual spreadsheet values.
- Apply category, numeric, and date filters consistently across the analysis.
- Explore a custom chart using validated axes, aggregation, sorting, and top-N.
- Preview duplicate removal and missing-value fills, then explicitly apply them to
  a separate working copy. Return to the original at any time.
- Download the current analysis as a PDF report, or filtered data as CSV/Excel.
- Switch light/dark themes and use responsive desktop, tablet, and mobile views.
- Delete the analysis session and its temporary data.

## Prerequisites

- Python **3.11 or 3.12** with `pip` and `venv`.
- Node.js **22 LTS** with npm.
- Two terminal windows for the local servers.

Commands below start in the repository root. No global Python packages need to be
changed. The backend uses an isolated virtual environment.

### Windows PowerShell

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe scripts/generate_samples.py
cd frontend
npm ci
```

Start the backend in one terminal, from the repository root:

```powershell
backend/.venv/Scripts/python.exe backend/run.py
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open **[http://127.0.0.1:5173](http://127.0.0.1:5173)**. Vite forwards `/api` requests to
Flask on port `5000`, keeping browser requests on the same origin. Use Ctrl+C in each
terminal to stop its server. Activation of the virtual environment is optional
because the commands call its interpreter directly.

After installation, Windows users can alternatively start both servers from one
terminal with `./scripts/start-dev.ps1`. That script writes logs under `artifacts/`
and stops both owned processes when you press Ctrl+C.

### macOS / Linux

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python scripts/generate_samples.py
cd frontend && npm ci
# Terminal 1, repository root:
backend/.venv/bin/python backend/run.py
# Terminal 2:
cd frontend && npm run dev
```

## Demonstration walkthrough

1. Choose **Explore Sample Dataset**, or use **Analyze Your Data** to upload a file.
2. For a workbook, select a worksheet. Review the table and inferred column types.
3. Open the dashboard to see actual metrics, automatically chosen charts and insights.
4. Filter a category or date range; all analytical sections recompute on the server.
5. Use chart exploration to change axes, aggregation, sorting, and category limits.
6. Review data quality, preview any cleaning operation, and confirm before applying.
7. Export a PDF or the currently selected data. Delete the session when finished.

The four bundled samples are **entirely synthetic**. Sales has dates and categories;
student performance has subject marks; expenses deliberately has no dates; inventory
has stock and warehouse information. `synthetic_student_workbook.xlsx` has two sheets
for demonstrating worksheet selection. Generate these deterministically with
`scripts/generate_samples.py`; see [sample data details](sample_data/README.md).

## Architecture

```text
frontend/                 React + Vite + TypeScript + Tailwind
  src/components/         Accessible shared UI and Recharts renderer
  src/pages/              Landing, upload and data workspace views
  src/hooks/              Theme and workspace state
  src/services/           Typed API requests and binary downloads
  src/types/              Shared response types
backend/                  Flask API
  app/analytics/          Pandas/NumPy profiling, filters and chart selection
  app/services/           File parsing, temporary sessions, cleaning and export
  tests/                  Engine and API regression tests
sample_data/              Reproducible fictional CSVs and multi-sheet workbook
scripts/                  Sample generator and live HTTP acceptance checks
API_CONTRACT.md           Request/response reference
```

The browser receives aggregates and paginated records rather than the full upload.
Every analysis/export request specifies its sheet, original/cleaned version, and
active filters. This avoids a hidden last-analysis state that could mix requests.
There is no `eval`, arbitrary query execution, macro execution, or LLM dependency.

## API

JSON endpoints return `{ "success": true, "data": ... }` or
`{ "success": false, "error": { "code": "...", "message": "..." } }` with appropriate
HTTP status codes. Binary exports return their media type and download filename.

Upload returns a cryptographically random `session_id` and ownership `token`.
All subsequent session requests require `X-Session-Token: <token>`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Availability and limits |
| POST | `/api/upload` | Multipart `file`; validate and create temporary session |
| GET | `/api/sheets/<session_id>` | Workbook sheet names |
| POST | `/api/preview/<session_id>` | Server-side pagination and search |
| POST | `/api/analyze/<session_id>` | Profile, metrics, charts, insights, quality |
| POST | `/api/filter/<session_id>` | Recompute analysis with validated filters |
| POST | `/api/custom-chart/<session_id>` | Validated axes, chart type and aggregation |
| POST | `/api/clean/<session_id>` | Preview with `apply: false`; apply with `true` |
| POST | `/api/export/<session_id>` | Current sheet/version/filters as PDF, CSV or XLSX |
| GET | `/api/export/<session_id>` | Unfiltered export using query parameters |
| POST | `/api/delete/<session_id>` | Delete temporary session |
| GET | `/api/samples` | List fictional demonstration datasets |
| GET | `/api/samples/<sample_id>` | Download a sample for the regular upload pipeline |

Example analysis body:

```json
{
  "sheet": "Data",
  "version": "original",
  "filters": { "Region": { "values": ["North"] } }
}
```

Use the actual sheet returned by upload. See [API_CONTRACT.md](API_CONTRACT.md) for
all request fields and response shapes.

## Analysis policy

- Column types are inferred from values. Identifiers and leading-zero codes are
  excluded from automatic numeric KPIs. No currency, revenue, dates, or subject
  meanings are invented when a dataset lacks them.
- Numeric parsing is deliberately conservative. Invalid/mixed values are reported;
  missing and non-finite values are excluded from numeric calculations.
- Native Excel dates and unambiguous ISO date strings can form time series.
  Ambiguous date strings are left unconverted and flagged for review.
- Charts depend on available columns: categorical comparisons, date trends,
  numeric distributions, relationships, and valid parts-of-a-whole breakdowns.
  High-cardinality charts use a clearly labeled top-N view.
- Outliers are potential unusual values under the **1.5 × IQR** rule, not proven
  errors. Pearson correlation describes association, not causation.
- Statistical results describe the uploaded/filtered observations only. The app
  does not predict outcomes or claim causal business explanations.
- Cleaning is opt-in, previews affected data, and preserves the original. Reapply
  all intended operations together; each cleaning plan starts from the original.
- Formula cells are never evaluated. Spreadsheet readers may expose cached values;
  formulas without cached results cannot contribute a calculated value. Text that
  could become a spreadsheet formula is escaped in downloadable CSV/Excel data.

## Configuration and limits

Set environment variables before starting Flask; `backend/.env.example` documents
them. The backend reads the process environment directly and does **not**
automatically load `.env` files.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Development server binding |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated CORS allowlist; use exact frontend origins in production |
| `MAX_UPLOAD_MB` | `10` | Maximum uploaded file size |
| `MAX_ROWS` | `50000` | Maximum data rows per worksheet |
| `MAX_COLUMNS` | `200` | Maximum columns per worksheet |
| `MAX_CELLS` | `1000000` | Maximum cells across a workbook |
| `MAX_SESSIONS` | `20` | Maximum active sessions per server process |
| `SESSION_TTL_SECONDS` | `3600` | Absolute session lifetime from upload |
| `SESSION_DIR` | `backend/instance/sessions` | Private temporary storage, ignored by Git |
| `REPORT_FONT` | Arial / DejaVu Sans when installed | Optional local TrueType font path for PDF report text |

Workbooks also have a 20-sheet limit, a 50 MiB expanded ZIP limit, and a 32,767
character cell limit. Files with macros or embedded objects in XLSX archives are
rejected. Readers handle UTF-8/BOM, UTF-16/BOM, and Windows-1252 CSV text and detect
comma, semicolon, tab, or pipe delimiters. Unsupported encodings should be resaved
as UTF-8. The first row is treated as column headers (up to 200 characters each).
Blank headers receive `Column N` names; duplicate headers receive numbered suffixes.

PDF glyph coverage depends on the installed report font; configure a suitable
Unicode TrueType font for datasets in scripts unsupported by the default font.

Session data is deleted on request. Cleanup checks expiry every 60 seconds while
running and on session requests; it may wait for active work to finish. Server
restart invalidates ownership tokens; expired orphaned temporary
directories are also cleaned up. One cleaned worksheet is retained per session.
The store is deliberately in-process: run one backend worker for this mini-project.

For example, in PowerShell:

```powershell
$env:MAX_UPLOAD_MB = "10"
$env:FRONTEND_ORIGINS = "http://127.0.0.1:5173"
backend/.venv/Scripts/python.exe backend/run.py
```

Frontend build variables are listed in `frontend/.env.example`. Set
`VITE_API_URL` only when the API is on a different origin, and align
`VITE_MAX_UPLOAD_MB` with the backend size limit when changing it. All frontend
environment values are public; never put secrets in them.

## Tests and production build

From the repository root on Windows:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

On macOS/Linux, replace the virtual environment interpreter with
`backend/.venv/bin/python`. With both servers running, exercise the API **through
the Vite proxy**:

```powershell
python scripts/acceptance_check.py --base-url http://127.0.0.1:5173
```

This uses real HTTP uploads and checks sales, academic Excel, multiple sheets,
no-date data, missing values, duplicates, filter aggregates, invalid files,
exports, categorical-only data, cleaning preservation, session ownership and
deletion. It removes its own uploaded sessions afterwards.

The Vite build writes `frontend/dist`. For deployment, serve that directory through
a web server and reverse-proxy `/api` to a production WSGI server. Keep API and
frontend on the same origin where possible. The provided Flask development server
is for local demonstrations. Do not put upload storage under a public web root.

## Privacy and scope

Uploads stay on the machine running Flask and are not sent to external analytics
or AI services. Files are temporary; treat sessions as disposable. This project is
intended for one local demonstration server, not a multi-tenant hosted service.
Production operation additionally needs HTTPS, deployment-specific resource limits,
monitoring, and a persistent/multi-worker session architecture if required.

Natural-language “Ask Your Data” is an optional future extension and is not
implemented. The existing typed analysis operations provide a controlled boundary
for adding it without executing generated code.

## References

- [Flask file upload and size limits](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [Pandas spreadsheet readers and engines](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)
- [Pandas CSV and Excel I/O](https://pandas.pydata.org/docs/user_guide/io.html)

Licensed under the [MIT License](LICENSE).
