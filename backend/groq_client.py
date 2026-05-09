"""
TalkERP – Groq LLM Client
Thin async wrapper around the Groq REST API with JSON extraction helpers.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from config import settings

logger = logging.getLogger("talkerp.groq")

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


# ---------------------------------------------------------------------------
# Raw Completion
# ---------------------------------------------------------------------------

async def groq_complete(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Call the Groq chat completion endpoint and return the assistant's
    message content as a raw string.
    """
    payload = {
        "model": settings.groq_model,
        "temperature": temperature if temperature is not None else settings.groq_temperature,
        "max_tokens": max_tokens or settings.groq_max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.groq_request_timeout) as client:
        response = await client.post(_GROQ_CHAT_URL, json=payload, headers=headers)
        response.raise_for_status()

    data = response.json()

    try:
        content: str = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Groq response structure: {data}") from exc

    logger.debug(
        "Groq tokens used: prompt=%d, completion=%d",
        data.get("usage", {}).get("prompt_tokens", 0),
        data.get("usage", {}).get("completion_tokens", 0),
    )
    return content


# ---------------------------------------------------------------------------
# JSON Parsing Helper
# ---------------------------------------------------------------------------

def extract_json(raw: str) -> dict[str, Any]:
    """
    Extract a JSON object from an LLM response.
    Handles bare JSON, code fences, and prose wrappers.
    """
    # 1. Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the first {...} block
    brace_match = re.search(r"\{[\s\S]+\}", raw)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response:\n{raw[:500]}")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

async def check_groq_connection() -> bool:
    """Return True if we can reach the Groq API with the configured key."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            return resp.status_code == 200
    except Exception as exc:
        logger.warning("Groq health check failed: %s", exc)
        return False
