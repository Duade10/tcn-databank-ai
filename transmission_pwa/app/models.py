from pydantic import BaseModel, Field, HttpUrl


class DatabankSource(BaseModel):
    id: str
    name: str
    description: str
    sheet_id: str
    sheet_url: HttpUrl | None = None
    source_type: str = "google_sheet"
    category: str
    voltage_levels: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    default_year: int | None = None
    default_month: int | None = None
    active: bool = True


class SourceCreate(BaseModel):
    name: str
    description: str
    sheet_url_or_id: str
    category: str = "Transmission line load management"
    tags: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str
    source_ids: list[str] | None = None
    mode: str = "answer"


class QueryResponse(BaseModel):
    answer: str
    selected_sources: list[str]
    context_rows: int
