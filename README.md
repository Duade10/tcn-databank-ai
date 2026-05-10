# TCN Databank AI

Mobile-first FastAPI PWA for querying power transmission station operational data in natural language.

The app is designed as a read-only operational databank. Operators and admins can ask questions such as peak load, low load, outage/status notes, line performance, DISCO-specific summaries, and daily reports. The first registered source is the Osogbo RCC 330/132kV line load-management tracker.

## Features

- Mobile-first PWA interface for station operators.
- FastAPI backend with JSON APIs.
- Natural-language AI answers and report generation.
- Admin dashboard for registering more Google Sheets later.
- Databank source registry in `transmission_pwa/data/sources.json`.
- Local workbook fallback for development.
- Read-only Google Sheets integration.
- Server-side credential handling only.

## Current Databank Source

The initial source is:

- **Name:** Osogbo RCC 330/132kV Lines Load Management Tracking
- **Google Sheet ID:** `1jsxcy4UcJtn5cCXFC--zBrcexRD8oSvoelHiI9_aXRE`
- **Data type:** Daily hourly line load readings
- **Coverage:** May 1-30, 2026 in the uploaded seed workbook
- **Fields normalized:** date, ACC, transmission interface, voltage level, line nomenclature, DISCO, hour, MW load value, operational status notes

The parser labels and indexes the workbook into normalized records. At the time of setup it produced:

- `26,654` total readings
- `26,195` numeric MW readings
- `459` operational/status readings
- ACCs: `AKURE ACC`, `AYEDE ACC`, `OSOGBO ACC`
- Voltage levels: `330kV`, `132kV`

## Repository Layout

```text
transmission_pwa/
  app/
    ai.py                  # AI context selection and OpenAI response handling
    config.py              # Environment configuration
    databank.py            # Google Sheets/workbook parsing and source registry
    main.py                # FastAPI app and API routes
    models.py              # Pydantic request/response models
    web/
      static/              # PWA JS, CSS, manifest, service worker, icon
      templates/           # HTML shell
  data/
    sources.json           # Registered databank sources
  requirements.txt
  README.md
```

## Safety Rules

This project must not write to the national Google Sheet.

The code uses:

```python
https://www.googleapis.com/auth/spreadsheets.readonly
```

There are no Google Sheets write, update, or delete routes in the app.

Do not commit secrets:

- `transmission_pwa/.env`
- local service-account JSON files
- uploaded operational workbooks

These are already covered by `.gitignore`.

## Setup

From the repository root:

```bash
cd transmission_pwa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
DATA_CACHE_SECONDS=300
PREFER_LOCAL_WORKBOOK=true
ALLOW_LOCAL_FALLBACK=false
QUERY_ARCHIVE_FIRST=true
ARCHIVE_DB_PATH=data/databank.sqlite
ADMIN_TOKEN=
```

Set `OPENAI_API_KEY` to enable AI answers and reports.

## Running Locally

```bash
cd transmission_pwa
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Local Workbook vs Live Google Sheet

By default:

```env
PREFER_LOCAL_WORKBOOK=true
```

This uses the uploaded workbook as a safe local seed during development.

To read the live Google Sheet instead:

```env
PREFER_LOCAL_WORKBOOK=false
```

The app will still use read-only Google Sheets credentials. By default, live-mode failures are surfaced instead of being hidden by stale local data.
Set `ALLOW_LOCAL_FALLBACK=true` only when you explicitly want that fallback behavior.

## Local Archive and Ingestion

The app can ingest live Google Sheet records into a local SQLite archive and answer from that archive first. This prevents data loss when the monthly Google Sheet is cleared.

Recommended production settings:

```env
PREFER_LOCAL_WORKBOOK=false
ALLOW_LOCAL_FALLBACK=false
QUERY_ARCHIVE_FIRST=true
ARCHIVE_DB_PATH=data/databank.sqlite
ADMIN_TOKEN=<long-random-secret>
```

Ingestion options:

- Use the Admin tab and tap **Ingest Live**.
- Or call the API:

```bash
curl -X POST https://databank.duade.work/api/ingest \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

For secure storage, keep the SQLite file outside Git, restrict it to the service user, and back it up off-server. For larger deployments, move the archive to managed PostgreSQL with encrypted storage, daily backups, and role-based database credentials.

## API Endpoints

```text
GET  /
GET  /api/sources
POST /api/sources
GET  /api/catalog
POST /api/query
```

Example query:

```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the highest load for 2SGB-YDE1 in May 2026?","mode":"answer"}'
```

## Adding New Sheets

Use the Admin tab in the PWA or call `POST /api/sources` with:

```json
{
  "name": "New Sheet Name",
  "description": "What this sheet contains",
  "sheet_url_or_id": "https://docs.google.com/spreadsheets/d/...",
  "category": "Transmission line load management",
  "tags": ["Osogbo RCC", "330kV", "132kV"]
}
```

Future sheets should be labeled with enough detail for the AI router to know when to use them.

## Notes

- The frontend is intentionally mobile-first.
- The app can be installed as a PWA from supported browsers.
- Without `OPENAI_API_KEY`, the backend returns a deterministic summary instead of a full AI-generated report.
