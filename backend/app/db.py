from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .config import settings

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)

def query(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        res = conn.execute(text(sql), params or {})
        return res.fetchall()

def execute(sql: str, params: dict | None = None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})