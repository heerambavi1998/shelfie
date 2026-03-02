from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from shelfie.config import get_settings
from shelfie.models import Direction, Read, ReadStatus
from shelfie.services.book_lookup import search_books
from shelfie.services.reads import ReadService
from shelfie.services.recommendations import RecommendationEngine
from shelfie.storage import Storage

_HERE = Path(__file__).resolve().parent

app = FastAPI(title="Shelfie", docs_url="/docs")
app.mount("/static", StaticFiles(directory=_HERE / "static"), name="static")
_templates = Jinja2Templates(directory=_HERE / "templates")


def _get_services() -> tuple[ReadService, RecommendationEngine]:
    settings = get_settings()
    storage = Storage(settings)
    return ReadService(storage, settings), RecommendationEngine(storage, settings)


# ── Pages ─────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _templates.TemplateResponse("index.html", {"request": request})


# ── API: Search ───────────────────────────────────────────────────────


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1)):
    settings = get_settings()
    results = search_books(q, google_api_key=settings.google_books_api_key)
    return [r.model_dump() for r in results]


# ── API: Reads ────────────────────────────────────────────────────────


class LogReadRequest(BaseModel):
    title: str
    author: str
    isbn: str = ""
    rating: int = Field(ge=1, le=5, default=3)
    review: str = ""
    status: str = "read"
    finished_at: str | None = None


@app.post("/api/reads")
async def api_log_read(body: LogReadRequest):
    read_service, _ = _get_services()

    status_map = {
        "read": ReadStatus.READ,
        "reading": ReadStatus.READING,
        "did-not-finish": ReadStatus.DNF,
        "dnf": ReadStatus.DNF,
    }
    status = status_map.get(body.status.lower(), ReadStatus.READ)

    finished_at: date | None = None
    if body.finished_at:
        try:
            finished_at = date.fromisoformat(body.finished_at)
        except ValueError:
            finished_at = date.today()
    elif status in (ReadStatus.READ, ReadStatus.DNF):
        finished_at = date.today()

    read = Read(
        title=body.title,
        author=body.author,
        isbn=body.isbn,
        status=status,
        rating=body.rating,
        review=body.review,
        finished_at=finished_at,
    )

    try:
        read = read_service.log_read(read)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return read.model_dump(mode="json")


@app.get("/api/reads")
async def api_list_reads(
    status: Optional[str] = None,
    min_rating: Optional[int] = None,
    year: Optional[int] = None,
):
    read_service, _ = _get_services()
    reads = read_service.list_reads(status=status, min_rating=min_rating, year=year)
    return [r.model_dump(mode="json") for r in reads]


@app.get("/api/reads/{read_id}")
async def api_get_read(read_id: str):
    read_service, _ = _get_services()
    read = read_service.get_read(read_id)
    if not read:
        raise HTTPException(status_code=404, detail="Read not found")
    return read.model_dump(mode="json")


# ── API: Recommendations ─────────────────────────────────────────────


class RecommendRequest(BaseModel):
    mood: str
    direction: str = "balance"


@app.post("/api/recommend")
async def api_recommend(body: RecommendRequest):
    _, rec_engine = _get_services()

    try:
        direction = Direction(body.direction)
    except ValueError:
        direction = Direction.BALANCE

    try:
        session = await rec_engine.recommend(body.mood, direction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return session.model_dump(mode="json")


@app.get("/api/sessions")
async def api_list_sessions():
    _, rec_engine = _get_services()
    sessions = rec_engine.get_sessions()
    return [s.model_dump(mode="json") for s in sessions]
