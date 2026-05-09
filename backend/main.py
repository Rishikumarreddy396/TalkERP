"""
TalkERP – FastAPI Application
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents import workflow
from config import settings
from database import check_db_connection, close_db_pool, init_db_pool
from groq_client import check_groq_connection
from models import (
    ExecutionOutput,
    GeneratorOutput,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SummarizerOutput,
    ValidatorOutput,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("talkerp.api")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== TalkERP starting up ===")
    await init_db_pool()
    yield
    logger.info("=== TalkERP shutting down ===")
    await close_db_pool()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Natural-language-to-SQL interface for ERP analytics, "
        "powered by LangGraph multi-agent orchestration and the Groq API."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred.", "error": str(exc)},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
async def health_check():
    """Liveness + readiness probe."""
    db_ok = await check_db_connection()
    groq_ok = await check_groq_connection()
    return HealthResponse(
        status="healthy" if (db_ok and groq_ok) else "degraded",
        db_connected=db_ok,
        groq_connected=groq_ok,
        version=settings.app_version,
    )


@app.post(
    "/api/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    tags=["TalkERP"],
    summary="Natural Language -> SQL -> Results -> Summary",
)
async def run_query(request: QueryRequest) -> QueryResponse:
    """
    Execute the full TalkERP multi-agent pipeline:

    1. Generator – translates the question into PostgreSQL.
    2. Validator – checks schema compliance, syntax, and security.
    3. Executor  – runs the query against the database.
    4. Summariser – produces a human-readable business summary.
    """
    t0 = time.perf_counter()
    logger.info(
        "Received query: %r (dry_run=%s)",
        request.question[:80],
        request.dry_run,
    )

    # ── Build initial state dict ──────────────────────────────────────
    initial_state = {
        "question": request.question,
        "max_rows": request.max_rows,
        "dry_run": request.dry_run,
        "max_retries": settings.max_validation_retries,
        "status": "pending",
        "retry_count": 0,
        "validation_attempts": 0,
        "query_results": [],
        "result_columns": [],
        "row_count": 0,
        "result_truncated": False,
        "tables_referenced": [],
        "validation_issues": [],
        "key_insights": [],
        "recommended_actions": [],
    }

    # ── Run the graph ─────────────────────────────────────────────────
    try:
        final_state: dict = await workflow.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("LangGraph workflow raised an unhandled exception.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution error: {exc}",
        )

    duration_ms = (time.perf_counter() - t0) * 1_000
    logger.info(
        "Workflow completed in %.1f ms (status=%s).",
        duration_ms,
        final_state.get("status"),
    )

    # ── Assemble response ────────────────────────────────────────────
    generator_out = None
    if final_state.get("generated_sql") or final_state.get("final_sql"):
        generator_out = GeneratorOutput(
            sql=final_state.get("final_sql") or final_state.get("generated_sql", ""),
            complexity=final_state.get("complexity", "moderate"),
            tables_referenced=final_state.get("tables_referenced", []),
        )

    validator_out = None
    if final_state.get("validation_attempts", 0) > 0:
        validator_out = ValidatorOutput(
            is_valid=final_state.get("is_valid", False),
            issues=final_state.get("validation_issues", []),
            corrected_sql=(
                final_state.get("final_sql")
                if final_state.get("final_sql") != final_state.get("generated_sql")
                else None
            ),
            validation_attempts=final_state.get("validation_attempts", 1),
        )

    execution_out = None
    if not request.dry_run and final_state.get("row_count", 0) > 0:
        execution_out = ExecutionOutput(
            rows=final_state.get("query_results", []),
            row_count=final_state.get("row_count", 0),
            columns=final_state.get("result_columns", []),
            execution_time_ms=final_state.get("execution_time_ms"),
            truncated=final_state.get("result_truncated", False),
        )

    summarizer_out = None
    if final_state.get("summary"):
        summarizer_out = SummarizerOutput(
            summary=final_state["summary"],
            key_insights=final_state.get("key_insights", []),
            recommended_actions=final_state.get("recommended_actions", []),
        )

    return QueryResponse(
        question=request.question,
        status=final_state.get("status", "failed"),
        generator=generator_out,
        validator=validator_out,
        execution=execution_out,
        summarizer=summarizer_out,
        error=final_state.get("error"),
        total_duration_ms=round(duration_ms, 1),
    )


@app.get("/api/schema", tags=["TalkERP"])
async def get_schema():
    """
    Return the list of permitted tables and their columns.
    Useful for the frontend's schema explorer panel.
    """
    from prompts import SAP_SCHEMA

    return {"schema": SAP_SCHEMA}
