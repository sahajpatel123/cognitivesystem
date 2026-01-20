"""
Legacy shim for config settings.

Use backend.app.config.settings (package) for typed settings. This module forwards to the new package to avoid breaking imports.
"""

from backend.app.config import (  # type: ignore
    Settings,
    get_settings,
    settings_public_summary,
    validate_for_env,
    redact_secrets,
    safe_error_detail,
    safe_dict,
)

settings = get_settings()
