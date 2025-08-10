from pydantic import BaseModel
from typing import Optional, List

class SearchResponseItem(BaseModel):
    id: int
    url: str
    repo: str
    title: Optional[str]
    snippet: str
    score: float

class SearchResponse(BaseModel):
    items: List[SearchResponseItem]

class TriageRequest(BaseModel):
    title: str
    body: str
    repo: Optional[str] = None
    k: int = 8

class TriageCandidate(BaseModel):
    id: int
    url: str
    title: Optional[str]
    snippet: str
    score: float

class TriageResponse(BaseModel):
    candidates: List[TriageCandidate]
    draft_reply: Optional[str] = None

class QARequest(BaseModel):
    question: str
    repo: Optional[str] = None
    k: int = 8

class QAResponse(BaseModel):
    answer: str
    citations: List[str]