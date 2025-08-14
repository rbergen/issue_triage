"""
Simple retrieval eval scaffold.
Provide a CSV in eval/goldsets with columns: query, expected_url (or pipe-separated list).
Computes Recall@k and MRR@k.
"""
import csv, argparse
from backend.app.config import settings
from backend.app.db import query
from backend.app.deps import get_openai_client


def retrieve(q: str, k: int = 5, repo: str | None = None):
    client = get_openai_client()
    if client is None:
        raise SystemExit("OpenAI client is not configured (missing API key). Aborting.")
    emb = client.embeddings.create(model=settings.embedding_model, input=q).data[0].embedding
    sql = (
        "SELECT url, (embedding <-> :vec) AS score FROM docs "
        + ("WHERE repo = :repo " if repo else "") +
        "ORDER BY embedding <-> :vec ASC LIMIT :k"
    )
    params = {"vec": emb, "k": k}
    if repo:
        params["repo"] = repo
    return query(sql, params)


def recall_mrr(golds: list[str], hits: list[str]):
    # golds can be multiple accepted URLs
    goldset = set(golds)
    recall = 1.0 if any(h in goldset for h in hits) else 0.0
    mrr = 0.0
    for i, h in enumerate(hits, start=1):
        if h in goldset:
            mrr = 1.0 / i
            break
    return recall, mrr


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--repo")
    args = ap.parse_args()

    R, M = [], []
    with open(args.file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row["query"]
            golds = [u.strip() for u in row["expected_url"].split("|")]
            rows = retrieve(q, k=args.k, repo=args.repo)
            hits = [r.url for r in rows]
            r, m = recall_mrr(golds, hits)
            R.append(r); M.append(m)
    import statistics as st
    print({"Recall@k": sum(R)/len(R), "MRR@k": sum(M)/len(M)})