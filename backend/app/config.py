import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = os.getenv("ENV", "development")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "14400"))  # 4 hours

    backend_public_base_url: str | None = os.getenv("BACKEND_PUBLIC_BASE_URL")
    cors_origins: List[str] = []
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_anon_key: str | None = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    database_url: str | None = os.getenv("DATABASE_URL")

    # Generic LLM / model provider config (model-agnostic)
    model_provider_api_key: str | None = os.getenv("MODEL_PROVIDER_API_KEY") or os.getenv("LLM_API_KEY")
    model_provider_base_url: str | None = os.getenv("MODEL_PROVIDER_BASE_URL") or os.getenv("LLM_API_BASE")
    llm_reasoning_model: str = os.getenv("LLM_REASONING_MODEL", "reasoning-model")
    llm_expression_model: str = os.getenv("LLM_EXPRESSION_MODEL", "expression-model")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_csv(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        return []

    def is_production(self) -> bool:
        return self.env.lower() == "production"

    def required_env_vars(self) -> list[str]:
        base_required = ["BACKEND_PUBLIC_BASE_URL", "CORS_ORIGINS", "MODEL_PROVIDER_API_KEY"]
        return base_required


settings = Settings()
