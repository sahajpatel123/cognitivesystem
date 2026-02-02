"""
Production-safe diagnostics for DB allowlist enforcement.
This module provides snapshot_db_allowlist_state() for debugging without exposing secrets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


def _extract_host_port(database_url: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract hostname and port from DATABASE_URL using urlparse.
    Uses parsed.hostname (never netloc) to avoid credential leakage.
    """
    if not database_url:
        return None, None
    try:
        parsed = urlparse(str(database_url))
        hostname = parsed.hostname
        port = parsed.port
        if hostname:
            hostname = hostname.lower()
        return hostname, port
    except Exception:
        return None, None


def _parse_allowlist_csv(allowlist_csv: Optional[str]) -> List[str]:
    """Parse CSV allowlist into list of stripped, non-empty entries."""
    if not allowlist_csv:
        return []
    return [item.strip().lower() for item in str(allowlist_csv).split(",") if item.strip()]


def _parse_entry(entry: str) -> Tuple[Optional[str], Optional[int]]:
    """Parse host or host:port entry. Returns (host, port_or_none)."""
    entry = entry.strip().lower()
    if not entry:
        return None, None
    if ":" in entry:
        parts = entry.rsplit(":", 1)
        try:
            port = int(parts[1])
            return parts[0], port
        except ValueError:
            return None, None
    return entry, None


def _check_match(
    db_host: Optional[str],
    db_port: Optional[int],
    allowlist_entries: List[str],
) -> bool:
    """Check if db_host:db_port matches any allowlist entry."""
    if not db_host:
        return False
    db_host_lower = db_host.lower()
    for entry in allowlist_entries:
        entry_host, entry_port = _parse_entry(entry)
        if not entry_host:
            continue
        if entry_port is not None:
            if db_host_lower == entry_host and db_port == entry_port:
                return True
        else:
            if db_host_lower == entry_host:
                return True
    return False


def snapshot_db_allowlist_state(
    database_url: Optional[str],
    allowlist_csv: Optional[str],
    app_env: str,
) -> Dict[str, Any]:
    """
    Return a production-safe snapshot of DB allowlist state.
    
    SAFE: Only returns hostname, port, allowlist entries (no credentials).
    NEVER returns netloc, username, password, or full DATABASE_URL.
    
    Returns:
        {
            "db_hostname": <hostname or None>,
            "db_port": <port or None>,
            "allowlist_entries": <list of entries>,
            "allowlist_count": <int>,
            "match": <bool>,
            "app_env": <string>,
        }
    """
    db_hostname, db_port = _extract_host_port(database_url)
    allowlist_entries = _parse_allowlist_csv(allowlist_csv)
    match = _check_match(db_hostname, db_port, allowlist_entries)
    
    return {
        "db_hostname": db_hostname,
        "db_port": db_port,
        "allowlist_entries": allowlist_entries,
        "allowlist_count": len(allowlist_entries),
        "match": match,
        "app_env": app_env,
    }
