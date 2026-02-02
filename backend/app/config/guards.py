from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Safe pattern for allowlist host entries: lowercase alphanumeric, dots, hyphens
_HOST_PATTERN = re.compile(r"^[a-z0-9.-]+$")


def _csv_list(text: Optional[str]) -> List[str]:
    """Split CSV text into list of stripped, non-empty items."""
    if text is None:
        return []
    return [item.strip() for item in str(text).split(",") if item.strip()]


def _extract_db_host_port(database_url: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract hostname and port from DATABASE_URL using urlparse.
    Uses parsed.hostname (never netloc) to avoid credential leakage.
    Returns (hostname_lowercase, port) or (None, None) on failure.
    """
    if not database_url:
        return None, None
    try:
        parsed = urlparse(str(database_url))
        hostname = parsed.hostname  # Never use netloc!
        port = parsed.port
        if hostname:
            hostname = hostname.lower()
        return hostname, port
    except Exception:
        return None, None


def _parse_allowlist_entry(entry: str) -> Tuple[Optional[str], Optional[int], bool]:
    """
    Parse a single allowlist entry (host or host:port).
    Returns (host_lowercase, port_or_none, is_valid).
    """
    entry = entry.strip().lower()
    if not entry:
        return None, None, False
    
    if ":" in entry:
        parts = entry.rsplit(":", 1)
        host_part = parts[0]
        port_part = parts[1]
        
        if not _HOST_PATTERN.match(host_part):
            return None, None, False
        
        try:
            port_int = int(port_part)
            if port_int < 1 or port_int > 65535:
                return None, None, False
            return host_part, port_int, True
        except ValueError:
            return None, None, False
    else:
        if not _HOST_PATTERN.match(entry):
            return None, None, False
        return entry, None, True


def _parse_and_validate_allowlist(allowlist_raw: List[str]) -> Tuple[List[Tuple[str, Optional[int]]], bool]:
    """
    Parse and validate all allowlist entries.
    Returns (list_of_(host, port_or_none), all_valid).
    """
    parsed = []
    for raw_entry in allowlist_raw:
        host, port, valid = _parse_allowlist_entry(raw_entry)
        if not valid:
            return parsed, False
        parsed.append((host, port))
    return parsed, True


def _host_matches(db_host: str, db_port: Optional[int], allowlist: List[Tuple[str, Optional[int]]]) -> bool:
    """
    Check if db_host:db_port matches any allowlist entry.
    
    Rules:
    - Entry (host, None): match if db_host == host (port ignored)
    - Entry (host, port): match only if db_host == host AND db_port == port
    """
    db_host_lower = db_host.lower()
    
    for entry_host, entry_port in allowlist:
        if entry_port is not None:
            # Entry has port - must match both
            if db_host_lower == entry_host and db_port == entry_port:
                return True
        else:
            # Entry is host only - match host regardless of port
            if db_host_lower == entry_host:
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

    # Cross-wire protection with robust host:port matching
    db_host, db_port = _extract_db_host_port(database_url)
    
    if app_env == "staging":
        if not allowlist_staging:
            raise ValueError("DB_HOST_ALLOWLIST_STAGING must be set (CSV) in staging")
        parsed_allowlist, all_valid = _parse_and_validate_allowlist(allowlist_staging)
        if not all_valid:
            raise ValueError("DB_HOST_ALLOWLIST_STAGING contains invalid entry")
        if not db_host:
            raise RuntimeError("DATABASE_URL host not in DB_HOST_ALLOWLIST_STAGING")
        if not _host_matches(db_host, db_port, parsed_allowlist):
            raise RuntimeError("DATABASE_URL host not in DB_HOST_ALLOWLIST_STAGING")
    elif app_env == "production":
        if not allowlist_prod:
            raise ValueError("DB_HOST_ALLOWLIST_PROD must be set (CSV) in production")
        parsed_allowlist, all_valid = _parse_and_validate_allowlist(allowlist_prod)
        if not all_valid:
            raise ValueError("DB_HOST_ALLOWLIST_PROD contains invalid entry")
        if not db_host:
            raise RuntimeError(
                f"DATABASE_URL host not in DB_HOST_ALLOWLIST_PROD "
                f"(host=<none>, port={db_port}, allowlist_count={len(parsed_allowlist)})"
            )
        if not _host_matches(db_host, db_port, parsed_allowlist):
            raise RuntimeError(
                f"DATABASE_URL host not in DB_HOST_ALLOWLIST_PROD "
                f"(host={db_host}, port={db_port}, allowlist_count={len(parsed_allowlist)})"
            )

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
