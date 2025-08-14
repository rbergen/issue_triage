"""Indexer script for GitHub issues/comments.

Reads a JSONL produced by fetch_github.py, chunks issue bodies and comments,
embeds the chunks with the configured embeddings model, and inserts rows
into the Postgres docs table (with pgvector embeddings).
"""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from typing import Any
from collections.abc import Sequence
from chunker import create_chunks_for_document
from config import DATABASE_URL, OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_TOKEN_LIMIT
from openai import OpenAI
import psycopg

# Per-request aggregate token budget for embeddings (sum across inputs)
PER_REQUEST_TOKEN_BUDGET = 300_000

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

CREATE_SQL = """
INSERT INTO docs (source_id, kind, repo, url, title, body, labels, created_at, updated_at, embedding)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (source_id) DO NOTHING;
"""

@dataclass(frozen=True, slots=True)
class DocRow:
    """Structured row destined for the `docs` table.

    Attributes:
        source_id: Stable identifier, e.g. "owner/repo#123" or with chunk suffix.
        kind: Either "issue" or "comment".
        repo: Repository in the form "owner/name".
        url: Canonical HTML URL for the source item.
        title: Human-readable chunk title; may include part numbering.
        body: Plaintext content of the chunk to embed/store.
        labels: List of label names assigned to the issue.
        created_at: ISO 8601 creation timestamp.
        updated_at: ISO 8601 update timestamp.
        token_count: Token count for `body` with the active embedding tokenizer.
    """
    source_id: str
    kind: str
    repo: str
    url: str | None
    title: str | None
    body: str
    labels: list[str]
    created_at: str | None
    updated_at: str | None
    token_count: int = 0

    def as_sql_params(self) -> tuple[Any, ...]:
        """Return values matching the placeholder order in CREATE_SQL."""
        # Order must match CREATE_SQL placeholders
        return (
            self.source_id,
            self.kind,
            self.repo,
            self.url,
            self.title,
            self.body,
            self.labels,
            self.created_at,
            self.updated_at,
        )

# Batch embeddings respecting per-request token budget

def embed_rows(rows: Sequence[DocRow]) -> list[list[float]]:
    """Embed rows in batches while honoring API token limits.

    Flushes the current batch whenever adding the next input would exceed the
    per-request aggregate token budget (PER_REQUEST_TOKEN_BUDGET). Each row is
    assumed to already respect the per-input cap (EMBEDDING_TOKEN_LIMIT) set by
    the embedding model.

    Args:
        rows: Sequence of DocRow instances to embed. `token_count` must reflect
            the tokenizer used by the embeddings model.

    Returns:
        A list of embedding vectors aligned with the input `rows` order.

    Raises:
        RuntimeError: If the OpenAI client is not configured.
        ValueError: If any row exceeds the per-input token limit.
    """
    if client is None:
        raise RuntimeError("OPENAI_API_KEY not configured")

    vectors: list[list[float]] = []
    batch_texts: list[str] = []
    batch_tokens = 0

    for row in rows:
        # Safety: per-input limit should have been enforced upstream (chunker)
        if row.token_count > EMBEDDING_TOKEN_LIMIT:
            raise ValueError(
                f"Row {row.source_id} exceeds per-input token limit: {row.token_count} > {EMBEDDING_TOKEN_LIMIT}"
            )

        # Flush current batch if adding this row would exceed the per-request budget
        if batch_texts and (batch_tokens + row.token_count > PER_REQUEST_TOKEN_BUDGET):
            resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch_texts)
            vectors.extend([d.embedding for d in resp.data])
            batch_texts.clear()
            batch_tokens = 0

        batch_texts.append(row.body)
        batch_tokens += row.token_count

    # Final flush
    if batch_texts:
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch_texts)
        vectors.extend([d.embedding for d in resp.data])

    return vectors

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--file", help="path to JSONL from fetch_github.py (auto if omitted)")
    ap.add_argument("--chunk-size", type=int, default=500, help="Maximum tokens per chunk")
    ap.add_argument("--overlap-size", type=int, default=100, help="Approximate token overlap between chunks")
    args = ap.parse_args()

    path = args.file or f".data/{args.repo.replace('/', '_')}_issues.jsonl"
    rows: list[DocRow] = []
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

            chunks = create_chunks_for_document(title, body, args.chunk_size, args.overlap_size, EMBEDDING_TOKEN_LIMIT)
            for chunk in chunks:
                chunk_id = f"{issue_id}" if len(chunks) == 1 else f"{issue_id}/chunk{chunk.chunk_id + 1}"
                rows.append(DocRow(
                    source_id=chunk_id,
                    kind="issue",
                    repo=args.repo,
                    url=url,
                    title=chunk.title,
                    body=chunk.text,
                    labels=labels,
                    created_at=created,
                    updated_at=updated,
                    token_count=chunk.token_count,
                ))

            # Process comments with chunking
            for idx, c in enumerate(comments):
                comment_body = c.get("body") or ""
                curl = c.get("html_url") or url
                ccreated = c.get("created_at")
                cupdated = c.get("updated_at")

                comment_title = f"Comment on: {title}" if title else f"Comment on issue #{issue['number']}"
                chunks = create_chunks_for_document(comment_title, comment_body, args.chunk_size, args.overlap_size, EMBEDDING_TOKEN_LIMIT)
                for chunk in chunks:
                    if len(chunks) == 1:
                        cid = f"{issue_id}/c{idx+1}"
                    else:
                        cid = f"{issue_id}/c{idx+1}/chunk{chunk.chunk_id + 1}"
                    rows.append(DocRow(
                        source_id=cid,
                        kind="comment",
                        repo=args.repo,
                        url=curl,
                        title=chunk.title,
                        body=chunk.text,
                        labels=labels,
                        created_at=ccreated,
                        updated_at=cupdated,
                        token_count=chunk.token_count,
                    ))

    batch_size = 256
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for row_index in range(0, len(rows), batch_size):
                batch_rows = rows[row_index:row_index + batch_size]
                embs = embed_rows(batch_rows)
                # Ensure counts match; zip(strict=True) will raise if not
                values = [(*r.as_sql_params(), e) for r, e in zip(batch_rows, embs, strict=True)]
                cur.executemany(CREATE_SQL, values)
        conn.commit()
    print(f"Indexed {len(rows)} rows for {args.repo}")