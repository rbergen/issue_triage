import argparse, json, os
from typing import List
from clean_text import md_to_text
from chunker import create_chunks_for_document
from config import DATABASE_URL, OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIM
from openai import OpenAI
import psycopg

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

CREATE_SQL = """
INSERT INTO docs (source_id, kind, repo, url, title, body, labels, created_at, updated_at, embedding)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (source_id) DO NOTHING;
"""

def embed_batch(texts: List[str]) -> List[List[float]]:
    if not client:
        raise RuntimeError("OPENAI_API_KEY not configured")
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in resp.data]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--file", help="path to JSONL from fetch_github.py (auto if omitted)")
    ap.add_argument("--chunk-size", type=int, default=500, help="Maximum tokens per chunk")
    ap.add_argument("--no-chunking", action="store_true", help="Disable chunking (use original behavior)")
    args = ap.parse_args()

    path = args.file or f".data/{args.repo.replace('/','_')}_issues.jsonl"
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            issue = item["issue"]
            comments = item["comments"]
            issue_id = f"{args.repo}#{issue['number']}"
            title = issue.get("title")
            body = issue.get("body") or ""
            url = issue.get("html_url")
            labels = [l["name"] for l in issue.get("labels", [])]
            created = issue.get("created_at")
            updated = issue.get("updated_at")

            # Process issue with chunking
            if args.no_chunking:
                # Original behavior - single document per issue
                clean_body = md_to_text(body)
                rows.append((issue_id, "issue", args.repo, url, title, clean_body, labels, created, updated))
            else:
                # New behavior - chunk large issues
                chunks = create_chunks_for_document(title, body, args.chunk_size)
                for chunk_idx, (chunk_title, chunk_body) in enumerate(chunks):
                    chunk_id = f"{issue_id}" if len(chunks) == 1 else f"{issue_id}/chunk{chunk_idx+1}"
                    rows.append((chunk_id, "issue", args.repo, url, chunk_title, chunk_body, labels, created, updated))

            # Process comments with chunking
            for idx, c in enumerate(comments):
                comment_body = c.get("body") or ""
                curl = c.get("html_url") or url
                ccreated = c.get("created_at")
                cupdated = c.get("updated_at")

                if args.no_chunking:
                    # Original behavior - single document per comment
                    cid = f"{issue_id}/c{idx+1}"
                    clean_comment_body = md_to_text(comment_body)
                    rows.append((cid, "comment", args.repo, curl, None, clean_comment_body, labels, ccreated, cupdated))
                else:
                    # New behavior - chunk large comments
                    comment_title = f"Comment on: {title}" if title else f"Comment on issue #{issue['number']}"
                    chunks = create_chunks_for_document(comment_title, comment_body, args.chunk_size)
                    for chunk_idx, (chunk_title, chunk_body) in enumerate(chunks):
                        if len(chunks) == 1:
                            cid = f"{issue_id}/c{idx+1}"
                        else:
                            cid = f"{issue_id}/c{idx+1}/chunk{chunk_idx+1}"
                        rows.append((cid, "comment", args.repo, curl, chunk_title, chunk_body, labels, ccreated, cupdated))

    texts = [ (r, r[5]) for r in rows ]
    B = 256
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(texts), B):
                batch_rows = rows[i:i+B]
                batch_texts = [r[5] for r in batch_rows]
                embs = embed_batch(batch_texts)
                values = []
                for (r, e) in zip(batch_rows, embs):
                    values.append((*r, e))
                cur.executemany(CREATE_SQL, values)
        conn.commit()
    print(f"Indexed {len(rows)} rows for {args.repo}")