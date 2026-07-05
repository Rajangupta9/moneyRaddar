"""Application configuration.

Loaded from environment / a local `.env` file. The project uses Groq as the
LLM provider (OpenAI-compatible API serving open models). The default model is
Llama 3.3 70B Versatile, overridable via `RUPEERADAR_LLM_MODEL`.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, sourced from env vars / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )

    # Groq API key — server-side only.
    groq_api_key: str | None = None

    # Model served by Groq. Default is a strong general model; swap to a fast
    # model (e.g. "llama-3.1-8b-instant") for high-volume categorization.
    rupeeradar_llm_model: str = "llama-3.3-70b-versatile"

    # Optional Groq base URL override (defaults to the SDK's endpoint).
    groq_base_url: str | None = None

    # Comma-separated allowed CORS origins (Vite dev server by default).
    rupeeradar_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Upload guard.
    rupeeradar_max_upload_mb: int = 10

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.rupeeradar_cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        """Phase 4 guardrail: app must run (degraded) without an API key."""
        return bool(self.groq_api_key)


settings = Settings()
