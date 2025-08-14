"""Database helpers for the Issue Triage API.

Provides a SQLAlchemy engine and simple query/execute wrappers.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .config import settings

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)


def query(sql: str, params: dict | None = None):
    """Execute a read-only SQL query and return all rows.

    Args:
        sql: SQL string with optional SQLAlchemy-style parameters (e.g., :name).
        params: Optional mapping of parameter values.
    Returns:
        A list-like of row objects accessible by attribute or index.
    """
    with engine.connect() as conn:
        res = conn.execute(text(sql), params or {})
        return res.fetchall()


def execute(sql: str, params: dict | None = None):
    """Execute a write statement within a transaction.

    Args:
        sql: SQL string with optional SQLAlchemy-style parameters.
        params: Optional mapping of parameter values.
    """
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})