"""
TalkERP – Configuration
Loads all settings from environment variables (or a .env file).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name:    str  = "TalkERP"
    app_version: str  = "1.0.0"
    debug:       bool = False

    # ── PostgreSQL ───────────────────────────────────────────────────────
    database_url:           str   = "postgresql://talkerp:password@localhost:5433/talkerp_db"
    db_pool_min:            int   = 2
    db_pool_max:            int   = 10
    db_query_timeout_sec:   float = 30.0

    # ── Groq ─────────────────────────────────────────────────────────────
    groq_api_key:          str   = ""
    groq_model:            str   = "llama-3.3-70b-versatile"
    groq_temperature:      float = 0.0
    groq_max_tokens:       int   = 2_048
    groq_request_timeout:  float = 60.0

    # ── LangGraph / Agents ───────────────────────────────────────────────
    max_validation_retries: int = 2
    max_result_rows:        int = 500

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


settings = Settings()
