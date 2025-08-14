"""Dependency providers for the Issue Triage API."""
from .config import settings
from openai import OpenAI

client = None


def get_openai_client() -> OpenAI | None:
    """Return a lazily initialized OpenAI client or None if not configured."""
    global client
    if settings.openai_api_key is None:
        return None
    if client is None:
        client = OpenAI(api_key=settings.openai_api_key)
    return client