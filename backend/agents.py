"""
TalkERP – LangGraph Multi-Agent Workflow
=========================================

Graph topology:

    START
      |
      v
  [generator_node]  ---- error ----------------------------> END
      |
      v
  [validator_node]  ---- is_valid=True -----------------> [executor_node]
      |                                                        |
      | is_valid=False + retries < max_retries                 |
      |                                                        v
      +----------------- [generator_node]            [summarizer_node]
                                                           |
      is_valid=False + retries exhausted --> END            v
                                                          END

Nodes return partial state-update dicts (LangGraph TypedDict pattern).
The executor node is skipped in dry_run mode.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph

from config import settings
from database import execute_query
from groq_client import extract_json, groq_complete
from models import AgentState
from prompts import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_TEMPLATE,
    SUMMARIZER_SYSTEM_PROMPT,
    SUMMARIZER_USER_TEMPLATE,
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_TEMPLATE,
)

logger = logging.getLogger("talkerp.agents")


# ===========================================================================
# NODE 1 – GENERATOR
# ===========================================================================

async def generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Translates the natural-language question into a PostgreSQL SELECT query.
    Returns partial state update dict.
    """
    question = state.get("question", "")
    max_rows = state.get("max_rows", 500)

    logger.info("[Generator] Processing question: %r", question[:80])

    user_prompt = GENERATOR_USER_TEMPLATE.format(
        question=question,
        max_rows=max_rows,
    )

    try:
        raw = await groq_complete(
            system_prompt=GENERATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        data = extract_json(raw)

        generated_sql = data["sql"].strip()
        complexity = data.get("complexity", "moderate")
        tables_referenced = data.get("tables_referenced", [])

        logger.info(
            "[Generator] SQL generated (complexity=%s, tables=%s)",
            complexity,
            tables_referenced,
        )

        return {
            "generated_sql": generated_sql,
            "complexity": complexity,
            "tables_referenced": tables_referenced,
            "status": "running",
        }

    except Exception as exc:
        logger.exception("[Generator] Failed to generate SQL.")
        return {
            "status": "failed",
            "error": f"SQL generation failed: {exc}",
        }


# ===========================================================================
# NODE 2 – VALIDATOR
# ===========================================================================

async def validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates the generated SQL against schema, security rules, and syntax.
    Returns partial state update dict.
    """
    validation_attempts = state.get("validation_attempts", 0) + 1
    logger.info("[Validator] Attempt %d — validating SQL.", validation_attempts)

    sql_to_check = state.get("generated_sql") or ""

    if not sql_to_check.strip():
        return {
            "is_valid": False,
            "validation_issues": ["No SQL was generated to validate."],
            "validation_attempts": validation_attempts,
            "status": "failed",
            "error": "Generator produced empty SQL.",
        }

    question = state.get("question", "")
    user_prompt = VALIDATOR_USER_TEMPLATE.format(
        question=question,
        sql=sql_to_check,
    )

    try:
        raw = await groq_complete(
            system_prompt=VALIDATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        data = extract_json(raw)

        is_valid = bool(data.get("is_valid", False))
        issues = data.get("issues", [])
        corrected = data.get("corrected_sql")

        if is_valid:
            final_sql = (corrected or sql_to_check).strip()
            logger.info("[Validator] SQL is valid.")
            return {
                "is_valid": True,
                "validation_issues": issues,
                "final_sql": final_sql,
                "validation_attempts": validation_attempts,
                "status": "success",
            }
        else:
            logger.warning("[Validator] Issues found: %s", issues)
            if corrected:
                logger.info("[Validator] Validator supplied a corrected SQL.")
                return {
                    "is_valid": True,
                    "validation_issues": issues,
                    "final_sql": corrected.strip(),
                    "validation_attempts": validation_attempts,
                    "status": "success",
                }
            else:
                retry_count = state.get("retry_count", 0) + 1
                return {
                    "is_valid": False,
                    "validation_issues": issues,
                    "validation_attempts": validation_attempts,
                    "retry_count": retry_count,
                    "generated_sql": None,
                    "status": "retrying",
                }

    except Exception as exc:
        logger.exception("[Validator] Validation call failed.")
        return {
            "validation_attempts": validation_attempts,
            "status": "failed",
            "error": f"Validation failed: {exc}",
        }


# ===========================================================================
# NODE 3 – EXECUTOR
# ===========================================================================

async def executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the validated SQL against PostgreSQL.
    Skipped entirely when dry_run is True.
    """
    if state.get("dry_run", False):
        logger.info("[Executor] dry_run=True — skipping execution.")
        return {}

    sql = state.get("final_sql")
    if not sql:
        return {
            "status": "failed",
            "error": "No validated SQL available for execution.",
        }

    max_rows = state.get("max_rows", 500)
    logger.info("[Executor] Executing SQL (max_rows=%d)...", max_rows)

    try:
        result = await execute_query(sql=sql, max_rows=max_rows)

        logger.info(
            "[Executor] %d rows in %.1f ms (truncated=%s).",
            result.row_count,
            result.execution_time_ms,
            result.truncated,
        )

        return {
            "query_results": result.rows,
            "result_columns": result.columns,
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms,
            "result_truncated": result.truncated,
        }

    except ValueError as exc:
        logger.error("[Executor] Safety guard rejected query: %s", exc)
        return {
            "status": "failed",
            "error": f"Query rejected by safety guard: {exc}",
        }

    except Exception as exc:
        logger.exception("[Executor] Database execution error.")
        return {
            "status": "failed",
            "error": f"Database error: {exc}",
        }


# ===========================================================================
# NODE 4 – SUMMARIZER
# ===========================================================================

async def summarizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Converts raw JSON query results into an executive business summary.
    """
    logger.info("[Summarizer] Building business summary...")

    query_results = state.get("query_results", [])
    results_json = json.dumps(
        query_results[:100], default=str, ensure_ascii=False
    )

    user_prompt = SUMMARIZER_USER_TEMPLATE.format(
        question=state.get("question", ""),
        sql=state.get("final_sql") or "(not executed — dry run)",
        results=results_json,
        row_count=state.get("row_count", 0),
        truncated=state.get("result_truncated", False),
    )

    try:
        raw = await groq_complete(
            system_prompt=SUMMARIZER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        data = extract_json(raw)

        logger.info("[Summarizer] Summary generated.")

        return {
            "summary": data.get("summary", ""),
            "key_insights": data.get("key_insights", []),
            "recommended_actions": data.get("recommended_actions", []),
            "status": "success",
        }

    except Exception as exc:
        logger.exception("[Summarizer] Summarisation failed.")
        return {
            "summary": "Summary could not be generated.",
            "status": "success",
            "error": f"Summariser warning: {exc}",
        }


# ===========================================================================
# ROUTING FUNCTIONS
# ===========================================================================

def route_after_generator(
    state: AgentState,
) -> Literal["validator", "end_with_error"]:
    """After generator: proceed to validation or abort."""
    if state.get("status") == "failed" or not state.get("generated_sql"):
        return "end_with_error"
    return "validator"


def route_after_validator(
    state: AgentState,
) -> Literal["executor", "generator", "end_with_error"]:
    """
    After validator:
    - Valid SQL   -> execute
    - Invalid, retries remain -> back to generator
    - Invalid, retries exhausted -> abort
    - Fatal error -> abort
    """
    if state.get("status") == "failed":
        return "end_with_error"

    if state.get("is_valid"):
        return "executor"

    max_retries = state.get("max_retries", 2)
    retry_count = state.get("retry_count", 0)

    if retry_count <= max_retries:
        logger.info(
            "[Router] Re-routing to generator (retry %d/%d).",
            retry_count,
            max_retries,
        )
        return "generator"

    logger.warning("[Router] Max retries exhausted — aborting.")
    return "end_with_error"


def route_after_executor(
    state: AgentState,
) -> Literal["summarizer", "end_with_error"]:
    """After executor: summarise or abort."""
    if state.get("status") == "failed":
        return "end_with_error"
    return "summarizer"


# ===========================================================================
# GRAPH CONSTRUCTION
# ===========================================================================

def build_graph():
    """
    Assemble and compile the TalkERP LangGraph workflow.
    Returns a compiled graph ready to be invoked with an AgentState dict.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────
    graph.add_node("generator", generator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("executor", executor_node)
    graph.add_node("summarizer", summarizer_node)

    # ── Entry point ───────────────────────────────────────────────────
    graph.add_edge(START, "generator")

    # ── Conditional edges ─────────────────────────────────────────────
    graph.add_conditional_edges(
        "generator",
        route_after_generator,
        {
            "validator": "validator",
            "end_with_error": END,
        },
    )

    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "executor": "executor",
            "generator": "generator",
            "end_with_error": END,
        },
    )

    graph.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "summarizer": "summarizer",
            "end_with_error": END,
        },
    )

    # ── Terminal node ─────────────────────────────────────────────────
    graph.add_edge("summarizer", END)

    return graph.compile()


# Module-level compiled graph (imported by main.py)
workflow = build_graph()
