import logging
import os
from dataclasses import dataclass, field
from typing import Set

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReleaseFlags:
    canary_enabled: bool = False
    canary_percent: int = 0
    canary_allowlist: Set[str] = field(default_factory=set)
    header_build_version_enabled: bool = True
    header_canary_enabled: bool = True
    chat_summary_canary_field_enabled: bool = True
    chat_summary_flags_field_enabled: bool = False


def parse_bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    lowered = val.strip().lower()
    if lowered in {"1", "true", "t", "yes", "y"}:
        return True
    if lowered in {"0", "false", "f", "no", "n"}:
        return False
    return default


def parse_int_clamped(val: str | None, default: int, lo: int, hi: int) -> int:
    if val is None:
        return default
    try:
        parsed = int(val)
    except Exception:
        return default
    return max(lo, min(hi, parsed))


def _parse_allowlist(val: str | None) -> Set[str]:
    if not val:
        return set()
    parts = [item.strip() for item in val.split(",")]
    return {p for p in parts if p}


def load_release_flags() -> ReleaseFlags:
    try:
        canary_enabled = parse_bool(os.environ.get("RELEASE_CANARY_ENABLED"), False)
        canary_percent = parse_int_clamped(os.environ.get("RELEASE_CANARY_PERCENT"), 0, 0, 100)
        canary_allowlist = _parse_allowlist(os.environ.get("RELEASE_CANARY_ALLOWLIST"))
        header_build_version_enabled = parse_bool(os.environ.get("RELEASE_HEADER_BUILD_VERSION"), True)
        header_canary_enabled = parse_bool(os.environ.get("RELEASE_HEADER_CANARY"), True)
        chat_summary_canary_field_enabled = parse_bool(os.environ.get("RELEASE_CHAT_SUMMARY_CANARY"), True)
        chat_summary_flags_field_enabled = parse_bool(os.environ.get("RELEASE_CHAT_SUMMARY_FLAGS"), False)
        return ReleaseFlags(
            canary_enabled=canary_enabled,
            canary_percent=canary_percent,
            canary_allowlist=canary_allowlist,
            header_build_version_enabled=header_build_version_enabled,
            header_canary_enabled=header_canary_enabled,
            chat_summary_canary_field_enabled=chat_summary_canary_field_enabled,
            chat_summary_flags_field_enabled=chat_summary_flags_field_enabled,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("release flags load failed; using defaults", extra={"err": str(exc)})
        return ReleaseFlags()
