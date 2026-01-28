import hashlib

from backend.app.release.flags import ReleaseFlags


def canary_bucket(request_id: str) -> int:
    h = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    prefix = h[:8]
    return int(prefix, 16) % 100


def decide_canary(request_id: str, subject_id: str | None, flags: ReleaseFlags) -> bool:
    if not flags.canary_enabled:
        return False
    if subject_id and subject_id in flags.canary_allowlist:
        return True
    bucket = canary_bucket(request_id)
    return bucket < flags.canary_percent
