"""Triage router: duplicate suggestion and draft reply generation."""

from fastapi import APIRouter, HTTPException
from ..schemas import TriageRequest, TriageResponse, TriageCandidate
from ..config import settings
from ..db import query
from ..deps import get_openai_client

router = APIRouter(prefix="/triage", tags=["triage"])

@router.post("/", response_model=TriageResponse)
def triage(req: TriageRequest):
    """Suggest duplicates and draft a reply using retrieved candidates."""
    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    q_text = f"{req.title}\n\n{req.body}".strip()
    emb = client.embeddings.create(model=settings.embedding_model, input=q_text).data[0].embedding

    sql = (
        "SELECT id, url, title, body, (embedding <-> :vec) AS score FROM docs "
        + ("WHERE repo = :repo " if req.repo else "") +
        "ORDER BY embedding <-> :vec ASC LIMIT :k"
    )
    params = {"vec": emb, "k": req.k}
    if req.repo:
        params["repo"] = req.repo
    rows = query(sql, params)

    cands = []
    context_blocks = []
    for r in rows:
        snippet = (r.body or "")[:300].replace("\n", " ")
        cands.append(TriageCandidate(id=r.id, url=r.url, title=r.title, snippet=snippet, score=float(r.score)))
        context_blocks.append(f"- {r.title or ''} ({r.url})\n{(r.body or '')[:800]}")

    # Draft reply with citations
    sys = "You draft concise, helpful GitHub issue replies. Always include inline citations with URLs provided."
    user = (
        "A new issue was created with the following content. "
        "Suggest a brief reply that points to possible duplicates, with links, and asks for any missing repro details.\n\n"
        f"NEW ISSUE:\nTitle: {req.title}\nBody: {req.body}\n\n"
        f"POSSIBLE DUPLICATES:\n{chr(10).join(context_blocks)}"
    )
    chat = client.chat.completions.create(
        model=settings.generation_model,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        temperature=0.2,
    )
    draft = chat.choices[0].message.content
    return TriageResponse(candidates=cands, draft_reply=draft)