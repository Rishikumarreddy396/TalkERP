"""
TalkERP – Database Layer
Async PostgreSQL connection pool via asyncpg with a safe query executor.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Optional, List, Dict

import asyncpg
from asyncpg import Pool

from config import settings

logger = logging.getLogger("talkerp.db")


# ---------------------------------------------------------------------------
# Connection Pool (singleton)
# ---------------------------------------------------------------------------

_pool: Optional[Pool] = None


async def init_db_pool() -> None:
    """Create the global connection pool. Call once at app startup."""
    global _pool
    if _pool is not None:
        return

    logger.info("Initialising PostgreSQL connection pool...")
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        command_timeout=settings.db_query_timeout_sec,
        server_settings={
            "default_transaction_read_only": "on",
            "application_name": "TalkERP",
        },
    )
    logger.info(
        "PostgreSQL pool ready (min=%d, max=%d).",
        settings.db_pool_min,
        settings.db_pool_max,
    )


async def close_db_pool() -> None:
    """Gracefully close the pool. Call at app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed.")


def get_pool() -> Pool:
    if _pool is None:
        raise RuntimeError(
            "Database pool is not initialised. Call init_db_pool() first."
        )
    return _pool


@asynccontextmanager
async def acquire():
    """Context manager that borrows a connection from the pool."""
    async with get_pool().acquire() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Safe Query Executor
# ---------------------------------------------------------------------------

_FORBIDDEN_KEYWORDS = frozenset(
    {
        "insert", "update", "delete", "drop", "truncate",
        "alter", "create", "grant", "revoke", "execute",
        "call", "do", "copy", "vacuum", "analyze",
    }
)


def _check_query_safety(sql: str) -> None:
    """
    Lightweight pre-execution guard.
    Raises ValueError on any detected unsafe statement.
    """
    first_word = sql.strip().split()[0].lower().rstrip(";")
    if first_word in _FORBIDDEN_KEYWORDS:
        raise ValueError(
            f"Forbidden SQL operation detected: '{first_word.upper()}'"
        )

    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise ValueError(
            "Stacked queries (multiple statements) are not permitted."
        )


class QueryResult:
    """Thin wrapper around asyncpg fetch results."""

    def __init__(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        execution_time_ms: float,
        truncated: bool,
    ):
        self.rows = rows
        self.columns = columns
        self.row_count = len(rows)
        self.execution_time_ms = execution_time_ms
        self.truncated = truncated

    def to_json_str(self, max_rows: int = 100) -> str:
        sample = self.rows[:max_rows]
        return json.dumps(sample, default=str, ensure_ascii=False)


async def execute_query(sql: str, max_rows: int = 500) -> QueryResult:
    """Execute a read-only SQL query with a hard row cap."""
    _check_query_safety(sql)

    normalised = sql.strip().rstrip(";")
    if "limit" not in normalised.lower():
        normalised = f"{normalised}\nLIMIT {max_rows}"
        logger.debug("No LIMIT clause found — injected LIMIT %d.", max_rows)

    logger.debug("Executing SQL:\n%s", normalised)

    t0 = time.perf_counter()
    async with acquire() as conn:
        await conn.execute("SET TRANSACTION READ ONLY")
        records: list[asyncpg.Record] = await conn.fetch(normalised)
    elapsed_ms = (time.perf_counter() - t0) * 1_000

    if not records:
        return QueryResult(
            rows=[], columns=[], execution_time_ms=elapsed_ms, truncated=False
        )

    columns = list(records[0].keys())
    rows = [dict(r) for r in records]
    truncated = len(rows) >= max_rows

    logger.info(
        "Query returned %d rows in %.1f ms (truncated=%s).",
        len(rows), elapsed_ms, truncated,
    )
    return QueryResult(
        rows=rows,
        columns=columns,
        execution_time_ms=elapsed_ms,
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

async def check_db_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        return False
