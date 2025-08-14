"""Q&A router: retrieval-augmented answering over indexed documents."""

from fastapi import APIRouter, HTTPException
from ..schemas import QARequest, QAResponse
from ..config import settings
from ..db import query
from ..deps import get_openai_client

router = APIRouter(prefix="/qa", tags=["qa"])

@router.post("/", response_model=QAResponse)
def qa(req: QARequest):
    """Answer a question using nearest retrieved documents as context."""
    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    embedding_response = client.embeddings.create(model=settings.embedding_model, input=req.question)
    if not embedding_response or not getattr(embedding_response, "data", None) or len(embedding_response.data) == 0 or not hasattr(embedding_response.data[0], "embedding"):
        raise HTTPException(status_code=500, detail="Failed to generate embedding")
    emb = embedding_response.data[0].embedding

    base_sql = "SELECT url, title, body, (embedding <-> :vec) AS score FROM docs"
    where_clause = " WHERE repo = :repo" if req.repo else ""
    order_limit = " ORDER BY embedding <-> :vec ASC LIMIT :k"
    sql = base_sql + where_clause + order_limit

    params = {"vec": emb, "k": req.k}
    if req.repo:
        params["repo"] = req.repo
    rows = query(sql, params)

    contexts = []
    citations = []
    for r in rows:
        contexts.append(f"Title: {r.title or ''}\nURL: {r.url}\nContent:\n{(r.body or '')[:1500]}")
        citations.append(r.url)

    sys = "You answer questions using only the provided context. Keep answers concise and include inline citations [n] that map to a citations list."
    numbered = [f"[{i+1}] {c}" for i, c in enumerate(contexts)]
    user = "\n\n".join(numbered) + f"\n\nQuestion: {req.question}\nAnswer with references like [1], [2]."

    chat = client.chat.completions.create(
        model=settings.generation_model,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        temperature=0.1,
    )

    if not chat.choices or len(chat.choices) == 0 or not getattr(chat.choices[0].message, "content", None):
        raise HTTPException(status_code=500, detail="Failed to generate answer")

    answer = chat.choices[0].message.content or ""
    return QAResponse(answer=answer, citations=citations)