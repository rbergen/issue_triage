"""Pydantic request/response schemas for API endpoints."""

from pydantic import BaseModel

class SearchResponseItem(BaseModel):
    """One search hit returned to the client."""
    id: int
    url: str
    repo: str
    title: str | None
    snippet: str
    score: float

class SearchResponse(BaseModel):
    """Container for semantic search results."""
    items: list[SearchResponseItem]

class TriageRequest(BaseModel):
    """Request payload for duplicate detection and draft reply generation."""
    title: str
    body: str
    repo: str | None = None
    k: int = 8

class TriageCandidate(BaseModel):
    """One candidate duplicate returned to the client."""
    id: int
    url: str
    title: str | None
    snippet: str
    score: float

class TriageResponse(BaseModel):
    """Response containing candidates and an optional drafted reply."""
    candidates: list[TriageCandidate]
    draft_reply: str | None = None

class QARequest(BaseModel):
    """Request payload for Q&A over indexed documents."""
    question: str
    repo: str | None = None
    k: int = 8

class QAResponse(BaseModel):
    """Answer and supporting citations."""
    answer: str
    citations: list[str]