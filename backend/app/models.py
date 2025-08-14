"""Pydantic models representing database documents and search results."""

from pydantic import BaseModel
from typing import Optional, List


class Doc(BaseModel):
    """Document model mirroring a row in the docs table."""

    id: int
    source_id: str
    kind: str
    repo: str
    url: str
    title: Optional[str]
    body: str
    labels: Optional[List[str]] = None
    created_at: Optional[str]
    updated_at: Optional[str]
    score: Optional[float] = None