"""Lightweight Markdown-to-text cleaning utilities.

Converts issue bodies/comments to plain text suitable for embedding and search.
"""
import re


def md_to_text(md: str) -> str:
    """Convert a Markdown/HTML-ish string to plain text for embeddings/search.

    Operations performed (intentionally lossy):
    - Remove fenced code blocks (``` ... ```), but keep inline code.
    - Strip HTML tags.
    - Convert Markdown links `[text](url)` into `text (url)`.
    - Drop heading markers and normalize list bullets to `- `.
    - Collapse all whitespace to single spaces.

    Args:
        md: Source string (Markdown/HTML allowed). Falsy values return "".

    Returns:
        A whitespace-normalized plain-text string preserving visible content and URLs.

    Example:
        >>> md_to_text("# Title\nSome [link](https://a/b).")
        'Title Some link (https://a/b).'
    """
    if not md:
        return ""
    # Strip code fences lightly but keep inline code
    md = re.sub(r"```[\s\S]*?```", "", md)
    # Remove HTML tags
    md = re.sub(r"<[^>]+>", " ", md)
    # Replace Markdown links [text](url) -> text (url)
    md = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1 (\2)", md)
    # Headings/bullets to plain text
    md = re.sub(r"^#+\s*", "", md, flags=re.MULTILINE)
    md = re.sub(r"^\s*[-*+]\s+", "- ", md, flags=re.MULTILINE)
    # Collapse whitespace
    md = re.sub(r"\s+", " ", md).strip()
    return md