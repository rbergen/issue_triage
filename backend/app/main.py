"""Issue Triage FastAPI application.

Exposes endpoints for semantic search, issue triage suggestions, and Q&A by
including the search, triage, and qa routers.
"""

from fastapi import FastAPI
from .routers import search, triage, qa

app = FastAPI(title="Issue Triage API")
app.include_router(search.router)
app.include_router(triage.router)
app.include_router(qa.router)