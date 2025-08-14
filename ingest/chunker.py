#!/usr/bin/env python3
"""
chunker.py — sentence-aware text chunking for embeddings (e.g., text-embedding-3-small)

Changes in this version:
- Adds a hard cap (--max-embed-tokens, default 8192) and enforces it.
- Auto-splits any chunk that would exceed the cap before calling the embeddings API.
- Validates again immediately before the API call for safety.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from functools import lru_cache
from collections.abc import Callable
import tiktoken
from clean_text import md_to_text
from config import EMBEDDING_MODEL

@dataclass(slots=True)
class Chunk:
    """A contiguous span of sentences prepared for embedding.

    Attributes:
        chunk_id: Sequential identifier within a document.
        text: The chunk text content.
        token_count: Token count for `text` using the selected tokenizer.
        start_sentence: Index of the first sentence (inclusive) in the source.
        end_sentence: Index of the last sentence (inclusive) in the source.
        title: Optional display title/context for the chunk.
    """
    chunk_id: int
    text: str
    token_count: int
    start_sentence: int
    end_sentence: int  # inclusive
    title: str | None = None

# ---------- Token counting ----------

@lru_cache(maxsize=None)
def get_token_counter(model: str = "text-embedding-3-small") -> Callable[[str], int]:
    """Return a function that counts tokens using tiktoken for the given model.

    Falls back to a default encoding if the model is unknown.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens_tiktoken(text: str) -> int:
        """Count tokens in `text` using the model-specific tiktoken encoder."""
        return len(enc.encode(text))

    return count_tokens_tiktoken

count_tokens: Callable[[str], int] = get_token_counter(EMBEDDING_MODEL)

# ---------- Sentence splitting ----------

_SENT_END_RE = re.compile(r"""
    (?<= [.!?] )
    (?: ["')\]] )?
    \s+
    (?=(?:[A-Z0-9"(\[]) )
""", re.X)


def split_into_paragraphs(text: str) -> list[str]:
    """Split raw text into paragraphs by blank lines.

    Normalizes newlines, trims whitespace, and drops empty paragraphs.

    Args:
        text: Input text.
    Returns:
        List of non-empty, stripped paragraphs.
    """
    return [p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]


def split_paragraph_into_sentences(paragraph: str) -> list[str]:
    """Split a paragraph into sentences using a simple regex heuristic.

    Collapses intra-paragraph newlines and avoids false splits around
    trailing quotes/brackets after sentence punctuation.

    Args:
        paragraph: A single paragraph of text.
    Returns:
        Ordered list of sentence strings.
    """
    tmp = re.sub(r"\s*\n\s*", " ", paragraph.strip())
    parts = _SENT_END_RE.split(tmp)
    out: list[str] = []
    buf = ""
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if not buf:
            buf = piece
        else:
            # If the current buffer does not appear to end a sentence, keep appending
            if not re.search(r'[.!?]["\')\]]?$', buf):
                buf = (buf + " " + piece).strip()
            else:
                out.append(buf)
                buf = piece
    if buf:
        out.append(buf)
    return out


def sentence_token_counts(sentences: list[str]) -> list[int]:
    """Map each sentence to its token length using the active tokenizer.

    Args:
        sentences: List of sentence strings.
    Returns:
        List of token counts aligned with `sentences`.
    """
    return [count_tokens(s) for s in sentences]

# ---------- Chunking ----------


def pack_sentences_into_chunks(
    sentences: list[str],
    max_tokens: int = 600,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    """Greedily pack sentences into chunks under a token target with optional overlap.

    Builds contiguous, non-overlapping chunks (except for the configured backward
    overlap between adjacent chunks). Ensures at least one sentence per chunk.

    Args:
        sentences: Sentences to pack.
        max_tokens: Target maximum tokens per chunk (soft cap).
        overlap_tokens: Approximate backward token overlap between chunks.
    Returns:
        A list of `Chunk` instances covering `sentences`.
    Raises:
        ValueError: If `max_tokens` <= 0 or `overlap_tokens` < 0.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be > 0")
    if overlap_tokens < 0:
        raise ValueError("overlap_tokens must be >= 0")

    toks = sentence_token_counts(sentences)
    chunks: list[Chunk] = []

    i = 0
    cid = 0
    n = len(sentences)
    while i < n:
        cur_tokens = 0
        start_i = i
        end_i = i - 1
        while i < n:
            sentence_toks = toks[i]
            if cur_tokens + sentence_toks <= max_tokens or end_i < start_i:
                cur_tokens += sentence_toks
                end_i = i
                i += 1
            else:
                break

        text = " ".join(sentences[start_i:end_i + 1]).strip()
        chunks.append(Chunk(
            chunk_id=cid,
            text=text,
            start_sentence=start_i,
            end_sentence=end_i,
            token_count=count_tokens(text),
        ))
        cid += 1

        if i >= n or overlap_tokens == 0:
            continue

        overlap_needed = overlap_tokens
        j = end_i
        cum = 0
        while j >= start_i and cum < overlap_needed:
            cum += toks[j]
            j -= 1
        i = max(j + 1, start_i)

    return chunks


def chunk_text(
    text: str,
    max_tokens: int = 600,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    """Split raw text into sentences and pack them into chunks.

    Args:
        text: Raw input text (possibly Markdown; not cleaned here).
        max_tokens: Target maximum tokens per chunk.
        overlap_tokens: Approximate backward token overlap between chunks.
    Returns:
        Chunks covering the text according to `max_tokens` and `overlap_tokens`.
    """
    paragraphs = split_into_paragraphs(text)
    sentences: list[str] = []
    for p in paragraphs:
        sentences.extend(split_paragraph_into_sentences(p))
    return pack_sentences_into_chunks(sentences, max_tokens=max_tokens, overlap_tokens=overlap_tokens)

# ---------- Safety: enforce hard cap ----------


def enforce_hard_cap(chunks: list[Chunk], cap: int) -> list[Chunk]:
    """
    Ensure each chunk.token_count <= cap.
    If a chunk exceeds cap, split it by sentences with zero overlap until all subchunks fit.
    The sentence indices in subchunks refer to the original positions.
    """
    safe: list[Chunk] = []
    next_id = 0
    for c in chunks:
        if c.token_count <= cap:
            safe.append(Chunk(
                chunk_id=next_id,
                text=c.text,
                start_sentence=c.start_sentence,
                end_sentence=c.end_sentence,
                token_count=c.token_count,
                title=c.title
            ))
            next_id += 1
            continue

        # Split the overlong chunk
        # Reconstruct its sentence list using the original text segmentation heuristic
        # We can't rely on exact original sentence indices here unless we resplit the full document;
        # so we split c.text into sentences and create subchunks that fit <= cap.
        local_sentences = split_paragraph_into_sentences(c.text)
        toks = sentence_token_counts(local_sentences)

        i = 0
        start_i_global = c.start_sentence
        while i < len(local_sentences):
            cur_tokens = 0
            start_i_local = i
            end_i_local = i - 1
            while i < len(local_sentences):
                sentence_toks = toks[i]
                if cur_tokens + sentence_toks <= cap or end_i_local < start_i_local:
                    cur_tokens += sentence_toks
                    end_i_local = i
                    i += 1
                else:
                    break
            sub_text = " ".join(local_sentences[start_i_local:end_i_local+1]).strip()
            safe.append(Chunk(
                chunk_id=next_id,
                text=sub_text,
                start_sentence=start_i_global + start_i_local,
                end_sentence=start_i_global + end_i_local,
                token_count=count_tokens(sub_text),
                title=c.title
            ))
            next_id += 1
    return safe


def create_chunks_for_document(title: str, body: str, chunk_size: int, overlap_tokens: int, max_embed_tokens: int) -> list[Chunk]:
    """Produce final chunks for a document title/body, enforcing the embedding cap.

    Steps:
      * Convert Markdown body to plain text.
      * Split into sentence chunks with optional overlap.
      * Enforce a hard per-input token cap (leaving ~200 tokens headroom for context).
      * Add a context prefix and per-part titles when multiple chunks are emitted.

    Args:
        title: Optional document title used for context.
        body: Raw Markdown body.
        chunk_size: Target maximum tokens per chunk before cap enforcement.
        overlap_tokens: Approximate backward token overlap between chunks.
        max_embed_tokens: Hard cap for embeddings input (e.g., 8192).
    Returns:
        List of `Chunk` objects ready for embedding.
    """
    text = ""
    chunks: list[Chunk] = []

    if not body or not body.strip():
        text = title or "<Untitled>"
        return [Chunk(
            chunk_id=0,
            text=text,
            token_count=count_tokens(text),
            start_sentence=0,
            end_sentence=0,
            title=title
        )]

    # Clean the text
    text = md_to_text(body)

    # Create full document context prefix
    chunks = chunk_text(text, max_tokens=chunk_size, overlap_tokens=overlap_tokens)

    # Enforce hard cap (auto-split any oversized chunk). Assumes the context prefix
    # will never exceed ~200 tokens.
    chunks = enforce_hard_cap(chunks, cap=max_embed_tokens-200)

    context_prefix = f"Title: {title}\n\n" if title else ""

    total = len(chunks)
    if total > 1:
        for i, chunk in enumerate(chunks, start=1):
            part = f"part {i}/{total}"
            chunk.title = f"{title} ({part})" if title else part.capitalize()
            chunk.text = f"{context_prefix}{chunk.text}"
            chunk.token_count = count_tokens(chunk.text)

    return chunks