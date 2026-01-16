from __future__ import annotations

import json
import os
from typing import Any, List

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = dict  # type: ignore

try:
    from pydantic import field_validator

    _PYDANTIC_V2 = True
except ImportError:  # pragma: no cover
    from pydantic import validator as field_validator  # type: ignore

    _PYDANTIC_V2 = False


def _parse_cors_origins(value: Any) -> list[str]:
    try:
        if value is None:
            return []
        if isinstance(value, list):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text == "*":
                return ["*"]
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
            except Exception:
                pass
            return [item.strip() for item in text.split(",") if item.strip()]
        return []
    except Exception:
        return []


class Settings(BaseSettings):
    if _PYDANTIC_V2:
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    else:  # pragma: no cover
        class Config:  # noqa: D106
            env_file = ".env"
            extra = "ignore"

    env: str = os.getenv("ENV", "development")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "14400"))

    backend_public_base_url: str | None = os.getenv("BACKEND_PUBLIC_BASE_URL")
    cors_origins: List[str] | str | None = []
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_anon_key: str | None = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    database_url: str | None = os.getenv("DATABASE_URL")

    model_provider_api_key: str | None = os.getenv("MODEL_PROVIDER_API_KEY") or os.getenv("LLM_API_KEY")
    model_provider_base_url: str | None = os.getenv("MODEL_PROVIDER_BASE_URL") or os.getenv("LLM_API_BASE")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    llm_api_base: str | None = os.getenv("LLM_API_BASE")
    llm_reasoning_model: str = os.getenv("LLM_REASONING_MODEL", "reasoning-model")
    llm_expression_model: str = os.getenv("LLM_EXPRESSION_MODEL", "expression-model")

    if _PYDANTIC_V2:

        @field_validator("cors_origins", mode="before")
        @classmethod
        def parse_cors_csv(cls, value: Any) -> list[str]:
            return _parse_cors_origins(value)

    else:  # pragma: no cover

        @field_validator("cors_origins", pre=True)
        def parse_cors_csv(cls, value: Any) -> list[str]:  # noqa: N805
            return _parse_cors_origins(value)

    def is_production(self) -> bool:
        return self.env.lower() == "production"

    def required_env_vars(self) -> list[str]:
        base_required = ["BACKEND_PUBLIC_BASE_URL", "CORS_ORIGINS", "MODEL_PROVIDER_API_KEY"]
        return base_required


settings = Settings()
