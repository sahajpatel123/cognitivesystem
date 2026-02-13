# Fix: HTTPS Detection Behind Railway Proxy

## Problem

The backend was returning "limited mode" fallback text instead of real LLM answers when deployed on Railway behind a reverse proxy. The issue occurred because:

1. **Root Cause**: Backend was using `request.url.scheme` directly, which shows `http` behind Railway's proxy even though the client connection is `https`
2. **Symptom**: Abuse detection added `non_https` penalty (10 points), combined with `anon_sensitive` (15 points) = 25 points
3. **Impact**: While not blocking (threshold is 70), the logs showed `abuse_reason: "anon_sensitive+non_https"` which indicated incorrect HTTPS detection

## Solution

### 1. Created Request Helper Utility (`backend/app/utils/request_helpers.py`)

New utility module to properly detect HTTPS behind reverse proxies:

```python
def get_request_scheme(request: Request) -> str:
    """
    Get actual request scheme, respecting X-Forwarded-Proto from proxy.
    Railway, Vercel, and other reverse proxies set this header.
    """
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        return forwarded_proto.lower().strip()
    return request.url.scheme
```

### 2. Updated Main Application (`backend/app/main.py`)

**Changes:**
- Import `get_request_scheme` helper
- Use `actual_scheme = get_request_scheme(request)` instead of `request.url.scheme`
- Pass `actual_scheme` to `AbuseContext.request_scheme`
- Added diagnostic logging showing:
  - `direct_scheme` (what FastAPI sees)
  - `x_forwarded_proto` (what proxy sends)
  - `actual_scheme` (what we use)
  - `is_https` (boolean)
  - Abuse detection results

### 3. Updated Fallback Text (`backend/mci_backend/fallback_rendering.py`)

Changed fallback message to be more specific:
- **Old**: "I'm currently operating in a limited mode and may not be able to provide a complete answer..."
- **New**: "I apologize, but I'm unable to generate a response right now due to a technical issue..."

This clarifies that fallback is for **LLM failures only**, not abuse/policy blocks.

### 4. Added Diagnostic Logging (`backend/mci_backend/model_invocation_pipeline.py`)

Added warning log when verification fails and fallback is triggered, showing:
- `model_ok`: Whether LLM call succeeded
- `model_has_text`: Whether LLM returned text
- `failure_type`: Why verification failed
- `failure_reason`: Specific reason code
- `output_action`: Expected action type

### 5. Created Test Script (`scripts/test_api_https.sh`)

Bash script to verify:
1. OPTIONS preflight returns correct CORS headers
2. POST with `X-Forwarded-Proto: https` returns real answer
3. Response doesn't contain fallback text
4. Response contains actual content about the question

## Verification

### Railway Deployment Configuration

The `start.sh` already has proxy headers enabled:
```bash
exec python3 -m uvicorn mci_backend.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "100.64.0.0/10"
```

This tells uvicorn to trust `X-Forwarded-*` headers from Railway's private network.

### Expected Log Output

After deployment, logs should show:
```json
{
  "message": "[HTTPS] Scheme detection",
  "request_id": "...",
  "direct_scheme": "http",
  "x_forwarded_proto": "https",
  "actual_scheme": "https",
  "is_https": true,
  "abuse_score": 15,
  "abuse_reason": "anon_sensitive",
  "abuse_action": "ALLOW"
}
```

**Key Changes:**
- `actual_scheme` should be `"https"` (not `"http"`)
- `abuse_reason` should be `"anon_sensitive"` only (no `+non_https`)
- `abuse_score` should be 15 (not 25)

### Testing Locally

```bash
# Test with X-Forwarded-Proto header
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -H "User-Agent: Mozilla/5.0" \
  -H "Accept: application/json" \
  -d '{"user_text":"What is Bitcoin?"}'
```

## Files Changed

### New Files (3)
1. `backend/app/utils/request_helpers.py` - HTTPS detection utility
2. `backend/app/utils/__init__.py` - Module exports
3. `scripts/test_api_https.sh` - Test script

### Modified Files (4)
1. `backend/app/main.py` - Use `get_request_scheme()` for abuse detection
2. `backend/mci_backend/fallback_rendering.py` - Updated fallback text
3. `backend/mci_backend/model_invocation_pipeline.py` - Added diagnostic logging
4. `backend/tests/test_regression_meta_scaffolding.py` - Updated test assertions

## Acceptance Criteria

✅ **Backend correctly detects HTTPS behind Railway proxy**
- Uses `X-Forwarded-Proto` header when present
- Falls back to `request.url.scheme` for direct connections

✅ **Abuse detection no longer penalizes HTTPS connections**
- `non_https` trigger removed when `X-Forwarded-Proto: https`
- Score reduced from 25 to 15 for anonymous requests

✅ **Diagnostic logging helps debug future issues**
- Shows all scheme detection inputs and outputs
- Logs verification failures with specific reason codes

✅ **Fallback text is appropriate**
- Only appears when LLM genuinely fails
- Clear message about technical issues
- No meta scaffolding or internal details

✅ **Tests verify correct behavior**
- Regression tests pass
- Test script validates end-to-end flow

## Next Steps

1. **Deploy to Railway** - Changes are backward compatible
2. **Monitor logs** - Check for `[HTTPS] Scheme detection` entries
3. **Verify production** - Ask "What is Bitcoin?" on production URL
4. **Confirm fix** - Response should contain real answer, not fallback text

## Related Issues

- Previous fix: Meta scaffolding bug (commit 7b2b67f)
- This fix: HTTPS detection behind proxy
- Both fixes work together to ensure real LLM answers reach users
