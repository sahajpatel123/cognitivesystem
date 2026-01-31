"""
DB allowlist diagnostics for testing only.

Returns structure-only information without secrets.
Never logs, never includes raw URLs, passwords, or full allowlist entries.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


_HOST_PATTERN = re.compile(r"^[a-z0-9.-]+$")


def _hash_entry(entry: str) -> str:
    """SHA256 hash of an allowlist entry for safe diagnostics."""
    return hashlib.sha256(entry.encode("utf-8")).hexdigest()[:16]


def _parse_allowlist(allowlist_csv: Optional[str]) -> tuple[List[str], Optional[str]]:
    """
    Parse and validate allowlist CSV.
    Returns (normalized_entries, error_reason_code).
    If error_reason_code is not None, entries may be partial.
    """
    if not allowlist_csv or not str(allowlist_csv).strip():
        return [], "MISSING_ALLOWLIST"
    
    entries = []
    for raw in str(allowlist_csv).split(","):
        entry = raw.strip().lower()
        if not entry:
            continue
        
        # Check if entry has port
        if ":" in entry:
            parts = entry.rsplit(":", 1)
            host_part = parts[0]
            port_part = parts[1]
            
            # Validate host part
            if not _HOST_PATTERN.match(host_part):
                return entries, "INVALID_ALLOWLIST_ENTRY"
            
            # Validate port part
            try:
                port_int = int(port_part)
                if port_int < 1 or port_int > 65535:
                    return entries, "INVALID_ALLOWLIST_ENTRY"
            except ValueError:
                return entries, "INVALID_ALLOWLIST_ENTRY"
        else:
            # Host only - validate
            if not _HOST_PATTERN.match(entry):
                return entries, "INVALID_ALLOWLIST_ENTRY"
        
        entries.append(entry)
    
    if not entries:
        return [], "MISSING_ALLOWLIST"
    
    return entries, None


def _check_host_allowed(
    db_host: str,
    db_port: Optional[int],
    allowlist_entries: List[str],
) -> bool:
    """
    Check if db_host:db_port is allowed by any entry in allowlist.
    
    Rules:
    - If entry is "host" (no port): match if db_host == entry (port ignored)
    - If entry is "host:port": match only if db_host == host AND db_port == port
    """
    db_host_lower = db_host.lower()
    
    for entry in allowlist_entries:
        if ":" in entry:
            # Entry has port - must match both host and port
            parts = entry.rsplit(":", 1)
            entry_host = parts[0]
            entry_port = int(parts[1])
            if db_host_lower == entry_host and db_port == entry_port:
                return True
        else:
            # Entry is host only - match host regardless of port
            if db_host_lower == entry:
                return True
    
    return False


def db_allowlist_diagnostics(
    database_url: Optional[str],
    app_env: Optional[str],
    allowlist_csv: Optional[str],
) -> Dict[str, Any]:
    """
    Return safe diagnostics for DB allowlist checking.
    
    NEVER includes:
    - Full DATABASE_URL
    - Username, password, query params
    - Raw allowlist entries
    - netloc (which may contain credentials)
    
    Returns only:
    - env: normalized env string
    - db_host: extracted hostname (lowercase) or None
    - db_port: parsed port int or None
    - allowlist_count: int
    - allowlist_first2_hashes: list of SHA256 hashes of first 2 entries
    - decision: "ALLOW" or "DENY"
    - reason_code: one of the defined codes
    """
    env = (app_env or "local").lower()
    
    # Parse DATABASE_URL
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    
    if not database_url or not str(database_url).strip():
        return {
            "env": env,
            "db_host": None,
            "db_port": None,
            "allowlist_count": 0,
            "allowlist_first2_hashes": [],
            "decision": "DENY",
            "reason_code": "MISSING_DATABASE_URL",
        }
    
    try:
        parsed = urlparse(str(database_url))
        db_host = parsed.hostname  # Never use netloc!
        db_port = parsed.port
    except Exception:
        return {
            "env": env,
            "db_host": None,
            "db_port": None,
            "allowlist_count": 0,
            "allowlist_first2_hashes": [],
            "decision": "DENY",
            "reason_code": "INVALID_DATABASE_URL",
        }
    
    if not db_host:
        return {
            "env": env,
            "db_host": None,
            "db_port": db_port,
            "allowlist_count": 0,
            "allowlist_first2_hashes": [],
            "decision": "DENY",
            "reason_code": "INVALID_DATABASE_URL",
        }
    
    db_host = db_host.lower()
    
    # Parse allowlist
    allowlist_entries, parse_error = _parse_allowlist(allowlist_csv)
    allowlist_count = len(allowlist_entries)
    allowlist_first2_hashes = [_hash_entry(e) for e in allowlist_entries[:2]]
    
    if parse_error:
        return {
            "env": env,
            "db_host": db_host,
            "db_port": db_port,
            "allowlist_count": allowlist_count,
            "allowlist_first2_hashes": allowlist_first2_hashes,
            "decision": "DENY",
            "reason_code": parse_error,
        }
    
    # Check if host is allowed
    if _check_host_allowed(db_host, db_port, allowlist_entries):
        return {
            "env": env,
            "db_host": db_host,
            "db_port": db_port,
            "allowlist_count": allowlist_count,
            "allowlist_first2_hashes": allowlist_first2_hashes,
            "decision": "ALLOW",
            "reason_code": "ALLOWED",
        }
    
    return {
        "env": env,
        "db_host": db_host,
        "db_port": db_port,
        "allowlist_count": allowlist_count,
        "allowlist_first2_hashes": allowlist_first2_hashes,
        "decision": "DENY",
        "reason_code": "HOST_NOT_ALLOWED",
    }
