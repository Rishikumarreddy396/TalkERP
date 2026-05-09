"""
TalkERP – Test Suite
Tests for agents (mocked LLM), database layer, and API routes.
Run with: pytest tests/ -v --asyncio-mode=auto
"""

from __future__ import annotations

import json
import sys
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import AgentState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Synchronous test client (no DB/Groq needed for unit tests)."""
    with patch("database.init_db_pool", new_callable=AsyncMock), \
         patch("database.close_db_pool", new_callable=AsyncMock):
        from main import app
        return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def base_state() -> dict:
    return {
        "question": "Which vendors have outstanding invoices over 90 days?",
        "max_rows": 100,
        "dry_run": False,
        "max_retries": 2,
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


# ---------------------------------------------------------------------------
# Prompt Sanity Tests
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_generator_prompt_contains_schema(self):
        from prompts import GENERATOR_SYSTEM_PROMPT
        assert "customer_master_kna1" in GENERATOR_SYSTEM_PROMPT
        assert "sales_header_vbak" in GENERATOR_SYSTEM_PROMPT
        assert "vendor_master_lfa1" in GENERATOR_SYSTEM_PROMPT

    def test_validator_prompt_contains_security_rules(self):
        from prompts import VALIDATOR_SYSTEM_PROMPT
        assert "DELETE" in VALIDATOR_SYSTEM_PROMPT
        assert "injection" in VALIDATOR_SYSTEM_PROMPT.lower()

    def test_all_prompts_forbid_dml(self):
        from prompts import GENERATOR_SYSTEM_PROMPT
        for keyword in ["DELETE", "UPDATE", "INSERT", "DROP"]:
            assert keyword in GENERATOR_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Generator Node Tests
# ---------------------------------------------------------------------------

class TestGeneratorNode:
    @pytest.mark.asyncio
    async def test_generator_happy_path(self, base_state):
        mock_response = json.dumps({
            "sql": "select sh.order_id, sh.order_date, sh.order_status from sales_header_vbak sh order by sh.order_date desc limit 100",
            "complexity": "simple",
            "tables_referenced": ["sales_header_vbak"],
            "estimated_cost": "low",
        })

        with patch("agents.groq_complete", new_callable=AsyncMock, return_value=mock_response):
            from agents import generator_node
            result = await generator_node(base_state)

        assert result.get("generated_sql") is not None
        assert "sales_header_vbak" in result["generated_sql"]
        assert result["complexity"] == "simple"
        assert result.get("status") != "failed"

    @pytest.mark.asyncio
    async def test_generator_handles_groq_error(self, base_state):
        with patch("agents.groq_complete", new_callable=AsyncMock, side_effect=Exception("Groq timeout")):
            from agents import generator_node
            result = await generator_node(base_state)

        assert result["status"] == "failed"
        assert "generation failed" in (result.get("error") or "").lower()


# ---------------------------------------------------------------------------
# Validator Node Tests
# ---------------------------------------------------------------------------

class TestValidatorNode:
    @pytest.mark.asyncio
    async def test_validator_accepts_valid_sql(self, base_state):
        base_state["generated_sql"] = (
            "select order_id, order_date from sales_header_vbak limit 100"
        )
        mock_response = json.dumps({
            "is_valid": True,
            "issues": [],
            "corrected_sql": None,
        })

        with patch("agents.groq_complete", new_callable=AsyncMock, return_value=mock_response):
            from agents import validator_node
            result = await validator_node(base_state)

        assert result["is_valid"] is True
        assert result["validation_issues"] == []

    @pytest.mark.asyncio
    async def test_validator_rejects_empty_sql(self, base_state):
        base_state["generated_sql"] = ""
        from agents import validator_node
        result = await validator_node(base_state)

        assert result["is_valid"] is False
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Database Safety Guard Tests
# ---------------------------------------------------------------------------

class TestDatabaseSafetyGuard:
    def test_blocks_delete(self):
        from database import _check_query_safety
        with pytest.raises(ValueError, match="Forbidden"):
            _check_query_safety("DELETE FROM sales_header_vbak WHERE 1=1")

    def test_blocks_drop(self):
        from database import _check_query_safety
        with pytest.raises(ValueError, match="Forbidden"):
            _check_query_safety("DROP TABLE sales_header_vbak")

    def test_blocks_stacked_queries(self):
        from database import _check_query_safety
        with pytest.raises(ValueError, match="Stacked"):
            _check_query_safety("SELECT 1; DROP TABLE sales_header_vbak")

    def test_allows_select(self):
        from database import _check_query_safety
        _check_query_safety("SELECT order_id FROM sales_header_vbak LIMIT 10")


# ---------------------------------------------------------------------------
# Routing Logic Tests
# ---------------------------------------------------------------------------

class TestRouting:
    def test_route_generator_to_validator_on_success(self, base_state):
        from agents import route_after_generator
        base_state["generated_sql"] = "select 1"
        base_state["status"] = "running"
        assert route_after_generator(base_state) == "validator"

    def test_route_generator_to_end_on_failure(self, base_state):
        from agents import route_after_generator
        base_state["status"] = "failed"
        assert route_after_generator(base_state) == "end_with_error"

    def test_route_validator_to_executor_when_valid(self, base_state):
        from agents import route_after_validator
        base_state["is_valid"] = True
        base_state["status"] = "success"
        assert route_after_validator(base_state) == "executor"

    def test_route_validator_retries_within_limit(self, base_state):
        from agents import route_after_validator
        base_state["is_valid"] = False
        base_state["retry_count"] = 1
        base_state["max_retries"] = 2
        base_state["status"] = "retrying"
        assert route_after_validator(base_state) == "generator"

    def test_route_validator_aborts_after_max_retries(self, base_state):
        from agents import route_after_validator
        base_state["is_valid"] = False
        base_state["retry_count"] = 3
        base_state["max_retries"] = 2
        base_state["status"] = "retrying"
        result = route_after_validator(base_state)
        assert result == "end_with_error"


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

class TestAPIRoutes:
    def test_health_endpoint_structure(self, client):
        with patch("main.check_db_connection", new_callable=AsyncMock, return_value=True), \
             patch("main.check_groq_connection", new_callable=AsyncMock, return_value=True):
            response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "db_connected" in body
        assert "groq_connected" in body

    def test_query_endpoint_validates_short_question(self, client):
        response = client.post("/api/query", json={"question": "hi"})
        assert response.status_code == 422

    def test_schema_endpoint_returns_tables(self, client):
        response = client.get("/api/schema")
        assert response.status_code == 200
        body = response.json()
        assert "schema" in body
        assert "customer_master_kna1" in body["schema"]


# ---------------------------------------------------------------------------
# Groq Client Tests
# ---------------------------------------------------------------------------

class TestGroqClient:
    def test_extract_json_from_bare_string(self):
        from groq_client import extract_json
        raw = '{"sql": "SELECT 1", "complexity": "simple"}'
        result = extract_json(raw)
        assert result["sql"] == "SELECT 1"

    def test_extract_json_from_fenced_block(self):
        from groq_client import extract_json
        raw = '```json\n{"is_valid": true, "issues": []}\n```'
        result = extract_json(raw)
        assert result["is_valid"] is True

    def test_extract_json_from_prose_wrapper(self):
        from groq_client import extract_json
        raw = 'Here is the result:\n{"summary": "All good."}\nDone.'
        result = extract_json(raw)
        assert result["summary"] == "All good."

    def test_extract_json_raises_on_garbage(self):
        from groq_client import extract_json
        with pytest.raises(ValueError, match="Could not extract"):
            extract_json("This is not JSON at all.")
