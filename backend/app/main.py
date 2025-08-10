from fastapi import FastAPI
from .routers import search, triage, qa

app = FastAPI(title="Issue Triage Copilot API")
app.include_router(search.router)
app.include_router(triage.router)
app.include_router(qa.router)