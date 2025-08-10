import re

def md_to_text(md: str) -> str:
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