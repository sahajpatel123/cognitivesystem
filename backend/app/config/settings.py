from __future__ import annotations

import functools
import json
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.config.guards import enforce_env_safety


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=("settings_",), case_sensitive=False)

    # App / env
    app_env: str = Field("local", alias="APP_ENV")
    debug_errors: int = Field(0, alias="DEBUG_ERRORS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    request_id_header: str = Field("x-request-id", alias="REQUEST_ID_HEADER")
    db_host_allowlist_staging: Optional[str] = Field(None, alias="DB_HOST_ALLOWLIST_STAGING")
    db_host_allowlist_prod: Optional[str] = Field(None, alias="DB_HOST_ALLOWLIST_PROD")

    # Legacy / compatibility
    backend_public_base_url: Optional[str] = Field(None, alias="BACKEND_PUBLIC_BASE_URL")
    cors_origins: Optional[str] = Field(None, alias="CORS_ORIGINS")
    database_url: Optional[str] = Field(None, alias="DATABASE_URL")
    supabase_url: Optional[str] = Field(None, alias="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: Optional[str] = Field(None, alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_aud: str = Field("authenticated", alias="SUPABASE_JWT_AUD")
    supabase_jwt_issuer: Optional[str] = Field(None, alias="SUPABASE_JWT_ISSUER")
    anon_session_ttl_days: int = Field(30, alias="ANON_SESSION_TTL_DAYS")
    identity_hash_salt: str = Field("dev-salt", alias="IDENTITY_HASH_SALT")
    auth_cookie_secure: bool = Field(False, alias="AUTH_COOKIE_SECURE")

    # Plan defaults
    plan_default: str = Field("free", alias="PLAN_DEFAULT")
    pro_subjects: Optional[str] = Field(None, alias="PRO_SUBJECTS")
    max_subjects: Optional[str] = Field(None, alias="MAX_SUBJECTS")

    # WAF
    waf_max_body_bytes: int = Field(200000, alias="WAF_MAX_BODY_BYTES")
    waf_max_user_text_chars: int = Field(8000, alias="WAF_MAX_USER_TEXT_CHARS")
    waf_ip_burst_limit: int = Field(5, alias="WAF_IP_BURST_LIMIT")
    waf_ip_burst_window_seconds: int = Field(10, alias="WAF_IP_BURST_WINDOW_SECONDS")
    waf_ip_sustain_limit: int = Field(60, alias="WAF_IP_SUSTAIN_LIMIT")
    waf_ip_sustain_window_seconds: int = Field(60, alias="WAF_IP_SUSTAIN_WINDOW_SECONDS")
    waf_subject_burst_limit: int = Field(8, alias="WAF_SUBJECT_BURST_LIMIT")
    waf_subject_burst_window_seconds: int = Field(10, alias="WAF_SUBJECT_BURST_WINDOW_SECONDS")
    waf_subject_sustain_limit: int = Field(120, alias="WAF_SUBJECT_SUSTAIN_LIMIT")
    waf_subject_sustain_window_seconds: int = Field(60, alias="WAF_SUBJECT_SUSTAIN_WINDOW_SECONDS")
    waf_lockout_schedule_seconds: str = Field("30,120,600,3600", alias="WAF_LOCKOUT_SCHEDULE_SECONDS")
    waf_lockout_cooldown_seconds: int = Field(21600, alias="WAF_LOCKOUT_COOLDOWN_SECONDS")
    waf_enforce_routes: str = Field("/api/chat", alias="WAF_ENFORCE_ROUTES")

    # Model provider (Step 7)
    model_calls_enabled: int = Field(1, alias="MODEL_CALLS_ENABLED")
    model_provider: str = Field("none", alias="MODEL_PROVIDER")
    model_name: str = Field("default", alias="MODEL_NAME")
    model_base_url: Optional[str] = Field(None, alias="MODEL_BASE_URL")
    model_provider_base_url: Optional[str] = Field(None, alias="MODEL_PROVIDER_BASE_URL")
    model_api_key: Optional[str] = Field(None, alias="MODEL_API_KEY")
    model_timeout_seconds: int = Field(30, alias="MODEL_TIMEOUT_SECONDS")
    model_connect_timeout_seconds: int = Field(10, alias="MODEL_CONNECT_TIMEOUT_SECONDS")
    model_max_output_tokens: int = Field(512, alias="MODEL_MAX_OUTPUT_TOKENS")
    model_max_input_tokens: int = Field(4096, alias="MODEL_MAX_INPUT_TOKENS")
    model_max_total_tokens: int = Field(4608, alias="MODEL_MAX_TOTAL_TOKENS")
    model_circuit_breaker_failures: int = Field(5, alias="MODEL_CIRCUIT_BREAKER_FAILURES")
    model_circuit_breaker_window_seconds: int = Field(60, alias="MODEL_CIRCUIT_BREAKER_WINDOW_SECONDS")
    model_circuit_breaker_open_seconds: int = Field(120, alias="MODEL_CIRCUIT_BREAKER_OPEN_SECONDS")

    # Performance budgets (Phase 16 Step 2)
    api_chat_total_timeout_ms: Optional[int] = Field(None, alias="API_CHAT_TOTAL_TIMEOUT_MS")
    model_call_timeout_ms: Optional[int] = Field(None, alias="MODEL_CALL_TIMEOUT_MS")
    outbound_http_timeout_s: Optional[float] = Field(None, alias="OUTBOUND_HTTP_TIMEOUT_S")
    outbound_http_connect_timeout_s: Optional[float] = Field(None, alias="OUTBOUND_HTTP_CONNECT_TIMEOUT_S")
    outbound_http_read_timeout_s: Optional[float] = Field(None, alias="OUTBOUND_HTTP_READ_TIMEOUT_S")
    outbound_http_max_connections: Optional[int] = Field(None, alias="OUTBOUND_HTTP_MAX_CONNECTIONS")
    outbound_http_max_keepalive_connections: Optional[int] = Field(None, alias="OUTBOUND_HTTP_MAX_KEEPALIVE_CONNECTIONS")
    outbound_http_keepalive_expiry_s: Optional[float] = Field(None, alias="OUTBOUND_HTTP_KEEPALIVE_EXPIRY_S")

    # Legacy LLM names (used by pipeline)
    llm_reasoning_model: str = Field("reasoning-model", alias="LLM_REASONING_MODEL")
    llm_expression_model: str = Field("expression-model", alias="LLM_EXPRESSION_MODEL")
    llm_api_base: Optional[str] = Field(None, alias="LLM_API_BASE")
    llm_api_key: Optional[str] = Field(None, alias="LLM_API_KEY")

    @field_validator(
        "model_calls_enabled",
        "debug_errors",
        "model_timeout_seconds",
        "model_connect_timeout_seconds",
        "model_max_output_tokens",
        "model_max_input_tokens",
        "model_max_total_tokens",
        "model_circuit_breaker_failures",
        "model_circuit_breaker_window_seconds",
        "model_circuit_breaker_open_seconds",
    )
    @classmethod
    def clamp_non_negative(cls, v: int) -> int:
        return max(0, v)

    @field_validator("app_env")
    @classmethod
    def normalize_env(cls, v: str) -> str:
        val = (v or "local").lower()
        if val == "dev":
            return "local"
        if val == "prod":
            return "production"
        return val

    def validated_caps(self) -> Dict[str, int]:
        max_output = max(1, self.model_max_output_tokens)
        max_input = max(1, self.model_max_input_tokens)
        max_total = max(max_output + max_input, self.model_max_total_tokens)
        if max_total < max_input:
            max_total = max_input
        if max_total < max_output:
            max_total = max_output
        return {
            "model_max_output_tokens": max_output,
            "model_max_input_tokens": max_input,
            "model_max_total_tokens": max_total,
        }

    @property
    def model_provider_api_key(self) -> Optional[str]:
        return self.model_api_key or self.llm_api_key

    @property
    def provider_base_url(self) -> Optional[str]:
        return self.model_base_url or self.model_provider_base_url or self.llm_api_base

    def cors_origins_list(self) -> List[str]:
        defaults = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        raw = self.cors_origins
        if raw is None or str(raw).strip() == "":
            return defaults
        text = str(raw).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                cleaned = [str(item).strip() for item in parsed if str(item).strip()]
                return cleaned or defaults
            if isinstance(parsed, str):
                parsed = parsed.strip()
                return [parsed] if parsed else defaults
        except Exception:
            # fall back to CSV parsing
            pass
        cleaned = [item.strip() for item in text.split(",") if item.strip()]
        return cleaned or defaults

    def required_env_vars(self) -> list[str]:
        return ["BACKEND_PUBLIC_BASE_URL", "CORS_ORIGINS", "MODEL_API_KEY"]


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    enforce_env_safety(settings)
    return settings


def validate_for_env(settings: Settings) -> Dict[str, Any]:
    issues: list[str] = []
    caps = settings.validated_caps()
    if settings.app_env == "production":
        if settings.debug_errors != 0:
            issues.append("DEBUG_ERRORS must be 0 in prod")
        if settings.model_calls_enabled not in (0, 1):
            issues.append("MODEL_CALLS_ENABLED must be 0 or 1")
        if settings.model_calls_enabled == 1 and settings.model_provider == "none":
            issues.append("MODEL_PROVIDER must be set in prod when calls enabled")
        if settings.model_calls_enabled == 1 and not settings.model_api_key and settings.model_provider not in (
            "custom",
            "local",
        ):
            issues.append("MODEL_API_KEY required in prod unless provider is custom/local")
    summary = settings_public_summary(settings, caps_override=caps)
    summary["issues"] = issues
    return summary


def settings_public_summary(settings: Optional[Settings] = None, *, caps_override: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    s = settings or get_settings()
    caps = caps_override or s.validated_caps()
    return {
        "env": s.app_env,
        "model_provider": s.model_provider,
        "model_name": s.model_name,
        "model_calls_enabled": bool(s.model_calls_enabled),
        "model_timeout_seconds": s.model_timeout_seconds,
        "model_connect_timeout_seconds": s.model_connect_timeout_seconds,
        "token_caps": caps,
    }


__all__ = ["Settings", "get_settings", "settings_public_summary", "validate_for_env"]
