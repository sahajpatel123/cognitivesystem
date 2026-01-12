import os
from pydantic import BaseModel


class Settings(BaseModel):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "14400"))  # 4 hours

    # Generic LLM config (model-agnostic)
    llm_api_base: str | None = os.getenv("LLM_API_BASE")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    llm_reasoning_model: str = os.getenv("LLM_REASONING_MODEL", "reasoning-model")
    llm_expression_model: str = os.getenv("LLM_EXPRESSION_MODEL", "expression-model")


settings = Settings()
