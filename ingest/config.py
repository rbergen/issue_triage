from dotenv import load_dotenv
load_dotenv()

import os
DATABASE_URL = os.getenv("HOST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/triage")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
EMBEDDING_TOKEN_LIMIT = int(os.getenv("EMBEDDING_TOKEN_LIMIT", "8192"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")