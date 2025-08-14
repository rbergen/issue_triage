# Issue Triage PoC

A practical RAG demo over public GitHub issues/comments. Ingests issues, indexes embeddings in pgvector, and exposes FastAPI endpoints for semantic search, duplicate suggestions (triage), and Q&A with citations.

## Quickstart

```bash
# 1) Copy and edit env
cp .env.example .env

# 2) Start db + api
docker compose up -d --build

# 3) Ingest a couple of public repos (e.g., fastapi/fastapi)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python ingest/fetch_github.py --repo fastapi/fastapi --max 200
python ingest/indexer.py --repo fastapi/fastapi

# 4) Try the API
open http://localhost:8000/docs

# 5) Streamlit UI
docker compose up -d ui
open http://localhost:8501
```

## Chunking strategy

This implementation includes intelligent text chunking to improve embedding quality and retrieval performance for long GitHub issues and comments.

## Features

### 1. Hierarchical Chunking Strategy

- **Paragraph-first**: Splits on double newlines to preserve semantic boundaries
- **Sentence-fallback**: Further splits long paragraphs by sentences
- **Word-level**: Last resort for extremely long sentences

### 2. Context Preservation

- **Overlap**: Configurable token overlap between chunks (default: 50 tokens)
- **Title propagation**: Chunk titles include original title + part numbering
- **Context prefix**: Each chunk includes document title for context

### 3. Flexible Configuration

- `--chunk-size`: Maximum tokens per chunk (default: 500)
- `--no-chunking`: Disable chunking for backward compatibility
- Smart token estimation (4 chars ≈ 1 token)

## Usage

### Basic Indexing with Chunking

```bash
# Default chunking (500 tokens per chunk)
python indexer.py --repo owner/repo

# Custom chunk size
python indexer.py --repo owner/repo --chunk-size 300

# Disable chunking (original behavior)
python indexer.py --repo owner/repo --no-chunking
```

### Database Migration

```bash
# Migrate existing database to support chunking
python migrate_db.py
```

### Testing Chunking

```bash
# Test the chunking logic
python test_chunking.py
```

## How It Works

### Original Approach

```text
GitHub Issue → Single Embedding → Database Row
```

### New Approach

```text
GitHub Issue → Smart Chunks → Multiple Embeddings → Multiple Database Rows
                   ↓
    Title: "Bug in parser"           Title: "Bug in parser (part 1/3)"
    Body: "Very long text..."   →    Body: "Title: Bug in parser\n\nVery long..."

                                     Title: "Bug in parser (part 2/3)"
                                     Body: "Title: Bug in parser\n\n...overlap + new content..."
```

### Chunk Naming Convention

- **Single chunk**: `owner/repo#123` (unchanged)
- **Multiple chunks**: `owner/repo#123/chunk1`, `owner/repo#123/chunk2`, etc.
- **Comments**: `owner/repo#123/c1/chunk1`, etc.

## Benefits

1. **Better Retrieval**: Small, focused chunks improve search relevance
2. **Embedding Quality**: Shorter, coherent text produces better embeddings
3. **Large Content Support**: Handles issues with 10K+ tokens
4. **Context Preservation**: Overlap and title prefixes maintain coherence
5. **Backward Compatibility**: Can be disabled with `--no-chunking`

## Technical Details

### Token Estimation

Uses character-based approximation (1 token ≈ 4 characters) for efficiency. More accurate than word-based counting for mixed content.

### Overlap Strategy

Each chunk includes the last ~50 tokens from the previous chunk to maintain context across boundaries.

## Performance Considerations

- **Index Size**: More chunks = larger index, but better retrieval quality
- **Embedding Costs**: More API calls for chunked documents
- **Query Performance**: Slightly more complex queries, but better result quality
