from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReadStatus(str, Enum):
    READING = "reading"
    READ = "read"
    DNF = "did-not-finish"


class Direction(str, Enum):
    EXPLORE_NEW = "explore-new"
    GO_DEEPER = "go-deeper"
    BALANCE = "balance"


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class Read(BaseModel):
    """A book you've read (or are reading), with your personal rating and review."""

    id: str = Field(default_factory=_new_id)
    title: str
    author: str
    isbn: str = ""
    status: ReadStatus = ReadStatus.READ
    rating: int = Field(ge=1, le=5, default=3)
    review: str = ""
    started_at: date | None = None
    finished_at: date | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    def to_doc(self) -> dict:
        """Serialize for TinyDB storage."""
        d = self.model_dump(mode="json")
        d["created_at"] = self.created_at.isoformat()
        if self.started_at:
            d["started_at"] = self.started_at.isoformat()
        if self.finished_at:
            d["finished_at"] = self.finished_at.isoformat()
        return d

    @classmethod
    def from_doc(cls, doc: dict) -> Read:
        return cls.model_validate(doc)


class MatchType(str, Enum):
    SAFE_BET = "safe bet"
    STRETCH_PICK = "stretch pick"
    WILD_CARD = "wild card"


class BookRecommendation(BaseModel):
    """A single book recommendation."""

    title: str
    author: str
    reason: str = Field(description="2-3 sentences explaining why THIS book for THIS reader right now")
    match_type: MatchType = Field(
        default=MatchType.SAFE_BET,
        description="'safe bet' = closely matches taste, 'stretch pick' = related but pushes boundaries, 'wild card' = surprising left-field pick"
    )


class RecommendationResponse(BaseModel):
    """A list of book recommendations from the engine."""

    recommendations: list[BookRecommendation] = Field(min_length=1, max_length=10)


class RecommendationSession(BaseModel):
    """A full recommendation request + response, stored for history."""

    id: str = Field(default_factory=_new_id)
    mood: str
    direction: Direction = Direction.BALANCE
    recommendations: list[BookRecommendation] = []
    created_at: datetime = Field(default_factory=datetime.now)

    def to_doc(self) -> dict:
        d = self.model_dump(mode="json")
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_doc(cls, doc: dict) -> RecommendationSession:
        return cls.model_validate(doc)


class BookSearchResult(BaseModel):
    """A book result from an external API search."""

    title: str
    author: str
    isbn: str = ""
    description: str = ""
    published_date: str = ""
    page_count: int = 0
    categories: list[str] = []
    average_rating: float = 0.0
    ratings_count: int = 0
    source: str = ""
    info_url: str = ""
