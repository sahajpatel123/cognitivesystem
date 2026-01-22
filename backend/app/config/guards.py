from __future__ import annotations

import logging
from typing import Iterable, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _csv_list(text: Optional[str]) -> List[str]:
    if text is None:
        return []
    return [item.strip() for item in str(text).split(",") if item.strip()]


def _extract_db_host(database_url: Optional[str]) -> Optional[str]:
    if not database_url:
        return None
    try:
        parsed = urlparse(database_url)
        return parsed.hostname
    except Exception:
        return None


def _host_matches(host: str, allowlist: Iterable[str]) -> bool:
    for entry in allowlist:
        if not entry:
            continue
        if host == entry or entry in host:
            return True
    return False


def _mask_host(host: Optional[str]) -> str:
    if not host:
        return "<none>"
    if len(host) <= 3:
        return host[0] + "***"
    return host[:3] + "***"


def enforce_env_safety(settings: object) -> None:
    """
    Enforces environment separation and safety gates. Raises ValueError/RuntimeError to fail fast.
    This must not log secrets or raw DATABASE_URL.
    """
    # Defensive attribute access (do not assume concrete type to avoid import cycles)
    app_env = str(getattr(settings, "app_env", "") or "local").lower()
    database_url = getattr(settings, "database_url", None)
    cors_origins_raw = getattr(settings, "cors_origins", None)
    cors_list_raw = []
    try:
        cors_list_raw = getattr(settings, "cors_origins_list")()
    except Exception:
        pass

    cors_list = [origin.rstrip("/") for origin in cors_list_raw if str(origin).strip()]
    debug_errors = getattr(settings, "debug_errors", 0)
    allowlist_staging = _csv_list(getattr(settings, "db_host_allowlist_staging", None))
    allowlist_prod = _csv_list(getattr(settings, "db_host_allowlist_prod", None))

    allowed_envs = {"local", "staging", "production"}
    if app_env not in allowed_envs:
        raise ValueError(f"APP_ENV must be one of {sorted(allowed_envs)}; got '{app_env}'")

    # Fail-fast for required fields in staging/prod
    if app_env in ("staging", "production"):
        if not (database_url and str(database_url).strip()):
            raise ValueError("DATABASE_URL is required in staging/production")
        if not cors_origins_raw or str(cors_origins_raw).strip() == "":
            raise ValueError("CORS_ORIGINS must be set and non-empty in staging/production")
        if not cors_list:
            raise ValueError("CORS_ORIGINS must parse to a non-empty list in staging/production")
        if debug_errors not in (0, False):
            raise ValueError("DEBUG_ERRORS must be 0 in staging/production")

    # Cross-wire protection
    db_host = _extract_db_host(database_url)
    if app_env == "staging":
        if not allowlist_staging:
            raise ValueError("DB_HOST_ALLOWLIST_STAGING must be set (CSV) in staging")
        if not db_host or not _host_matches(db_host, allowlist_staging):
            raise RuntimeError("DATABASE_URL host not in DB_HOST_ALLOWLIST_STAGING")
    elif app_env == "production":
        if not allowlist_prod:
            raise ValueError("DB_HOST_ALLOWLIST_PROD must be set (CSV) in production")
        if not db_host or not _host_matches(db_host, allowlist_prod):
            raise RuntimeError("DATABASE_URL host not in DB_HOST_ALLOWLIST_PROD")

    # CORS strictness
    if app_env == "production":
        if any(origin == "*" for origin in cors_list):
            raise ValueError("CORS_ORIGINS cannot include '*' in production")
        if any(origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1") for origin in cors_list):
            raise ValueError("CORS_ORIGINS cannot include localhost in production")
    elif app_env == "staging":
        if any(origin == "*" for origin in cors_list):
            raise ValueError("CORS_ORIGINS cannot include '*' in staging")

    logger.info(
        "[CFG_GUARD] env=%s cors_origins=%d db_host=%s guards=ok",
        app_env,
        len(cors_list),
        _mask_host(db_host),
    )
