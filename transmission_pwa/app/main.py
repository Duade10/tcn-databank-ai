from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ai import answer_question, select_context
from .config import get_settings
from .databank import (
    archive_summary,
    build_catalog,
    extract_sheet_id,
    ingest_sources,
    load_records_for_sources,
    list_sources,
    save_source,
    slugify,
)
from .models import DatabankSource, QueryRequest, QueryResponse, SourceCreate


APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / "web"

app = FastAPI(title="Transmission Station AI PWA")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/sources")
async def sources() -> list[DatabankSource]:
    return list_sources()


@app.post("/api/sources")
async def create_source(payload: SourceCreate, x_admin_token: str | None = Header(default=None)) -> DatabankSource:
    require_admin_token(x_admin_token)
    sheet_id = extract_sheet_id(payload.sheet_url_or_id)
    source = DatabankSource(
        id=slugify(payload.name),
        name=payload.name,
        description=payload.description,
        sheet_id=sheet_id,
        sheet_url=f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
        category=payload.category,
        tags=payload.tags,
    )
    try:
        return save_source(source)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/catalog")
async def catalog() -> dict:
    records = load_records_for_sources()
    return {**build_catalog(records), "archive": archive_summary()}


@app.get("/api/archive")
async def archive() -> dict:
    return archive_summary()


@app.post("/api/ingest")
async def ingest(x_admin_token: str | None = Header(default=None)) -> dict:
    require_admin_token(x_admin_token)
    return ingest_sources()


@app.post("/api/query", response_model=QueryResponse)
async def query(payload: QueryRequest) -> QueryResponse:
    records = load_records_for_sources(payload.source_ids)
    if not records:
        raise HTTPException(status_code=404, detail="No databank records are available for the selected source.")
    history = [message.model_dump() for message in payload.history]
    context = select_context(payload.question, records, history=history)
    answer = answer_question(payload.question, records, payload.mode, history=history)
    return QueryResponse(
        answer=answer,
        selected_sources=sorted({record["source_id"] for record in context}),
        context_rows=len(context),
    )


def require_admin_token(token: str | None) -> None:
    expected = get_settings().admin_token
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token.")
