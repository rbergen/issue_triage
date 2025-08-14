"""Search router: vector search over embedded documents."""
from fastapi import APIRouter, HTTPException
from ..schemas import SearchResponse, SearchResponseItem
from ..config import settings
from ..db import query
from ..deps import get_openai_client

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/", response_model=SearchResponse)
def search(q: str, repo: str | None = None, k: int = 8):
    """Search embedded docs by query embedding and vector distance.

    Args:
        q: Natural language query.
        repo: Optional repo filter (owner/name).
        k: Max number of results to return.
    """
    # Embed the query
    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    emb = client.embeddings.create(model=settings.embedding_model, input=q).data[0].embedding

    # Use cosine distance operator <#> for normalized vectors, or L2 <-> if not normalized
    # Here we use L2; for cosine, store normalized vectors at index time.
    sql = (
        "SELECT id, url, repo, title, body, (embedding <-> :vec) AS score "
        "FROM docs "
        + ("WHERE repo = :repo " if repo else "") +
        "ORDER BY embedding <-> :vec ASC LIMIT :k"
    )
    params = {"vec": emb, "k": k}
    if repo:
        params["repo"] = repo
    rows = query(sql, params)

    items = []
    for r in rows:
        body = r.body or ""
        snippet = body[:300].replace("\n", " ")
        items.append(SearchResponseItem(id=r.id, url=r.url, repo=r.repo, title=r.title, snippet=snippet, score=float(r.score)))
    return SearchResponse(items=items)