# Transmission Station AI PWA

FastAPI-powered PWA for querying Power Transmission Station operational data in natural language.

Google Sheets credentials are configured locally through `GOOGLE_SERVICE_ACCOUNT_FILE`. The app only requests read-only spreadsheet scope and does not implement any Google Sheet write, update, or delete operation.

## Current Databank Source

- Name: Osogbo RCC 330/132kV Lines Load Management Tracking
- Google Sheet: `1jsxcy4UcJtn5cCXFC--zBrcexRD8oSvoelHiI9_aXRE`
- Local seed workbook: `../5. OSOGBO RCC - (330_132kV LINES) LOAD MANAGEMENT TRACKING - MAY 2026.xlsx`
- Data type: daily 330kV/132kV line load-management readings by ACC, transmission interface, voltage, line nomenclature, DISCO, and hourly MW/status values.

## Setup

```bash
cd transmission_pwa
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` for AI answers and reports.
Set `QUERY_ARCHIVE_FIRST=true` and run ingestion to keep a local SQLite archive of live sheet data before the source sheet is cleared.

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.
