"""
TalkERP – Pydantic Models
Covers API I/O and the shared LangGraph AgentState (as TypedDict).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    RETRYING = "retrying"


class QueryComplexity(str, Enum):
    SIMPLE   = "simple"
    MODERATE = "moderate"
    COMPLEX  = "complex"


# ---------------------------------------------------------------------------
# LangGraph – Shared State (TypedDict for LangGraph compatibility)
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """
    The single state object that flows through every LangGraph node.
    Using TypedDict for full LangGraph compatibility.
    Nodes return partial dicts to update specific keys.
    """
    # ── Input ────────────────────────────────────────────────────────────
    question: str
    max_rows: int
    dry_run: bool

    # ── Generator ────────────────────────────────────────────────────────
    generated_sql: Optional[str]
    complexity: Optional[str]
    tables_referenced: list[str]

    # ── Validator ────────────────────────────────────────────────────────
    is_valid: Optional[bool]
    validation_issues: list[str]
    final_sql: Optional[str]
    validation_attempts: int

    # ── Execution ────────────────────────────────────────────────────────
    query_results: list[dict[str, Any]]
    result_columns: list[str]
    row_count: int
    execution_time_ms: Optional[float]
    result_truncated: bool

    # ── Summarizer ───────────────────────────────────────────────────────
    summary: Optional[str]
    key_insights: list[str]
    recommended_actions: list[str]

    # ── Control flow ─────────────────────────────────────────────────────
    status: str
    error: Optional[str]
    retry_count: int
    max_retries: int


# ---------------------------------------------------------------------------
# API – Request
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Incoming natural-language query from the frontend."""

    question: str = Field(
        ...,
        min_length=5,
        max_length=2_000,
        description="Natural-language business question.",
        examples=["Which vendors have the most overdue deliveries this quarter?"],
    )
    max_rows: int = Field(
        default=500,
        ge=1,
        le=5_000,
        description="Hard cap on rows returned from the database.",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, the SQL is validated but NOT executed.",
    )


# ---------------------------------------------------------------------------
# API – Response
# ---------------------------------------------------------------------------

class GeneratorOutput(BaseModel):
    sql: str
    complexity: str
    tables_referenced: list[str]
    estimated_cost: Optional[str] = None

class ValidatorOutput(BaseModel):
    is_valid: bool
    issues: list[str] = Field(default_factory=list)
    corrected_sql: Optional[str] = None
    validation_attempts: int = 1

class ExecutionOutput(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    columns: list[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None
    truncated: bool = False

class SummarizerOutput(BaseModel):
    summary: str
    key_insights: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)

class QueryResponse(BaseModel):
    """Full response returned to the frontend."""
    question: str
    status: str

    generator:  Optional[GeneratorOutput]  = None
    validator:  Optional[ValidatorOutput]  = None
    execution:  Optional[ExecutionOutput]  = None
    summarizer: Optional[SummarizerOutput] = None

    error: Optional[str] = None
    total_duration_ms: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    groq_connected: bool
    version: str = "1.0.0"
