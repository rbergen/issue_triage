from pydantic import BaseModel
from typing import Optional, List

class Doc(BaseModel):
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