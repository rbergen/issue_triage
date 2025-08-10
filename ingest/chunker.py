import re
from typing import List, Tuple
from clean_text import md_to_text

def count_tokens(text: str) -> int:
    """Rough token count approximation (1 token ≈ 4 chars for English)"""
    return len(text) // 4

def smart_chunk_text(text: str, max_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
    """
    Split text into chunks with smart boundaries, preserving context.

    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between consecutive chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # If text is short enough, return as single chunk
    if count_tokens(text) <= max_tokens:
        return [text.strip()]

    chunks = []

    # First, try splitting on double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    current_chunk = ""
    current_tokens = 0

    for paragraph in paragraphs:
        para_tokens = count_tokens(paragraph)

        # If single paragraph is too long, split it further
        if para_tokens > max_tokens:
            # Save current chunk if it exists
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0

            # Split long paragraph by sentences
            sentence_chunks = _split_long_paragraph(paragraph, max_tokens, overlap_tokens)
            chunks.extend(sentence_chunks)
            continue

        # If adding this paragraph would exceed limit, save current chunk
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap from previous chunk
            overlap_text = _get_overlap_text(current_chunk, overlap_tokens)
            current_chunk = overlap_text + "\n\n" + paragraph if overlap_text else paragraph
            current_tokens = count_tokens(current_chunk)
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_tokens += para_tokens

    # Add final chunk
    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def _split_long_paragraph(paragraph: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """Split a long paragraph by sentences"""
    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)

    chunks = []
    current_chunk = ""
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        # If single sentence is too long, split by words as last resort
        if sentence_tokens > max_tokens:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0

            word_chunks = _split_by_words(sentence, max_tokens, overlap_tokens)
            chunks.extend(word_chunks)
            continue

        # If adding sentence would exceed limit, save current chunk
        if current_tokens + sentence_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap
            overlap_text = _get_overlap_text(current_chunk, overlap_tokens)
            current_chunk = overlap_text + " " + sentence if overlap_text else sentence
            current_tokens = count_tokens(current_chunk)
        else:
            # Add sentence to current chunk
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_tokens += sentence_tokens

    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def _split_by_words(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """Last resort: split by words"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_tokens = 0

    for word in words:
        word_tokens = count_tokens(word)

        if current_tokens + word_tokens > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap
            overlap_words = _get_overlap_words(current_chunk, overlap_tokens)
            current_chunk = overlap_words + [word]
            current_tokens = count_tokens(" ".join(current_chunk))
        else:
            current_chunk.append(word)
            current_tokens += word_tokens

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def _get_overlap_text(text: str, overlap_tokens: int) -> str:
    """Get the last N tokens worth of text for overlap"""
    if overlap_tokens <= 0:
        return ""

    words = text.split()
    # Approximate: take last words that sum to roughly overlap_tokens
    overlap_chars = overlap_tokens * 4

    result = ""
    for word in reversed(words):
        if len(result) + len(word) + 1 > overlap_chars:
            break
        result = word + " " + result if result else word

    return result.strip()

def _get_overlap_words(words: List[str], overlap_tokens: int) -> List[str]:
    """Get the last N tokens worth of words for overlap"""
    if overlap_tokens <= 0:
        return []

    overlap_chars = overlap_tokens * 4
    result = []
    char_count = 0

    for word in reversed(words):
        if char_count + len(word) + 1 > overlap_chars:
            break
        result.insert(0, word)
        char_count += len(word) + 1

    return result

def create_chunks_for_document(title: str, body: str, max_tokens: int = 500) -> List[Tuple[str, str]]:
    """
    Create chunks for a document (issue or comment).

    Returns:
        List of (chunk_title, chunk_body) tuples
    """
    if not body or not body.strip():
        return [(title or "", "")]

    # Clean the text
    clean_body = md_to_text(body)

    # Create full document context prefix
    context_prefix = ""
    if title:
        context_prefix = f"Title: {title}\n\n"

    # Get text chunks
    chunks = smart_chunk_text(clean_body, max_tokens)

    if len(chunks) <= 1:
        # Single chunk - return original
        return [(title or "", clean_body)]

    # Multiple chunks - add context and numbering
    result = []
    for i, chunk in enumerate(chunks, 1):
        chunk_title = f"{title} (part {i}/{len(chunks)})" if title else f"Part {i}/{len(chunks)}"
        chunk_body = context_prefix + chunk
        result.append((chunk_title, chunk_body))

    return result
