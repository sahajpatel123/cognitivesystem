# Fix: LLM Adapter HTTP Request Failed - Detailed Diagnostics + URL Fix

## Problem
Railway logs showed:
```
MODEL_VERIFY_FAIL failure_type=PROVIDER_ERROR reason_code=EXTERNAL_DEPENDENCY_FAILURE 
parse_error="LLM adapter HTTP request failed"
has_output_json=false has_output_text=false
```

The LLM HTTP request was failing but the error message didn't reveal:
- The actual HTTP status code
- The final URL being called
- The response body from OpenAI
- Whether it was a timeout, DNS error, or HTTP error

## Root Causes

### 1. Missing `/chat/completions` Endpoint
**File**: `backend/app/llm_client.py` line 174 (old)
```python
resp = client.post(self.api_base, headers=headers, json=payload, timeout=timeout)
```

The code posted directly to `self.api_base` (e.g., `https://api.openai.com/v1`) without appending `/chat/completions`.

**Correct**: Should be `https://api.openai.com/v1/chat/completions`

### 2. No URL Normalization
If env var was set to `https://api.openai.com` (without `/v1`), or `https://api.openai.com/v1/chat/completions` (with full path), the code didn't normalize it.

### 3. Error Details Lost
**File**: `backend/app/llm_client.py` lines 190-195 (old)
```python
except httpx.HTTPError as exc:
    raise build_failure(
        violation_class=ViolationClass.EXTERNAL_DEPENDENCY_FAILURE,
        reason="LLM adapter HTTP request failed",
        detail={"error": str(exc)},  # Only generic string, no status code or response
    ) from exc
```

This caught all HTTP errors (4xx, 5xx, connection, DNS, timeout) and only logged `str(exc)`, losing:
- HTTP status codes (401, 404, 429, 500, etc.)
- Response body from OpenAI (which contains error details)
- URL that was actually called
- Exception type (timeout vs connection vs HTTP error)

## The Fix

### 1. Added URL Normalization (lines 41-62)

```python
def _normalize_base_url(base_url: str) -> str:
    """Normalize base URL to ensure correct OpenAI endpoint format.
    
    Accepts:
    - https://api.openai.com -> https://api.openai.com/v1
    - https://api.openai.com/v1 -> https://api.openai.com/v1
    - https://api.openai.com/v1/ -> https://api.openai.com/v1
    - https://api.openai.com/v1/chat/completions -> https://api.openai.com/v1
    
    Returns base URL ending with /v1 (no trailing slash, no /chat/completions)
    """
    base_url = base_url.rstrip("/")
    
    # Remove /chat/completions if present
    if base_url.endswith("/chat/completions"):
        base_url = base_url[:-len("/chat/completions")]
    
    # Ensure /v1 is present
    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"
    
    return base_url
```

Applied in `__init__` (line 140):
```python
raw_base = api_base or s.model_base_url or s.model_provider_base_url or s.llm_api_base or _resolve_api_base()
self.api_base = _normalize_base_url(raw_base) if raw_base else None
```

### 2. Fixed Endpoint Path (line 185)

```python
# Build full URL with /chat/completions endpoint
url = f"{self.api_base}/chat/completions"
```

Now correctly builds: `https://api.openai.com/v1/chat/completions`

### 3. Added Detailed Error Logging

**Request logging** (lines 200-209):
```python
logger.info(
    "[LLM] HTTP request",
    extra={
        "url": url,
        "model": payload.get("model"),
        "timeout_s": self.timeout_seconds,
        "request_id": self.request_id_value,
    }
)
```

**Success logging** (lines 217-223):
```python
logger.info(
    "[LLM] HTTP response OK",
    extra={
        "status_code": resp.status_code,
        "model": payload.get("model"),
    }
)
```

**HTTP Status Errors (4xx, 5xx)** (lines 252-274):
```python
except httpx.HTTPStatusError as exc:
    # HTTP error with response (4xx, 5xx)
    status_code = exc.response.status_code
    response_text = exc.response.text[:300] if exc.response.text else ""
    logger.error(
        "[LLM] HTTP error",
        extra={
            "url": url,
            "status_code": status_code,
            "response_preview": response_text,
            "error_type": type(exc).__name__,
        }
    )
    raise build_failure(
        violation_class=ViolationClass.EXTERNAL_DEPENDENCY_FAILURE,
        reason=f"LLM adapter HTTP {status_code} error",
        detail={
            "error": str(exc),
            "status_code": status_code,
            "response_preview": response_text,
            "url": url,
        },
    ) from exc
```

**Timeout Errors** (lines 237-251):
```python
except httpx.TimeoutException as exc:
    logger.error(
        "[LLM] HTTP timeout",
        extra={
            "url": url,
            "timeout_s": self.timeout_seconds,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    )
    raise build_failure(
        violation_class=ViolationClass.EXTERNAL_DEPENDENCY_FAILURE,
        reason="LLM adapter HTTP request timeout",
        detail={"error": str(exc), "url": url, "timeout_s": self.timeout_seconds},
    ) from exc
```

**Connection/DNS Errors** (lines 275-289):
```python
except httpx.HTTPError as exc:
    # Other HTTP errors (connection, DNS, etc.)
    logger.error(
        "[LLM] HTTP connection error",
        extra={
            "url": url,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    )
    raise build_failure(
        violation_class=ViolationClass.EXTERNAL_DEPENDENCY_FAILURE,
        reason="LLM adapter HTTP request failed",
        detail={"error": str(exc), "error_type": type(exc).__name__, "url": url},
    ) from exc
```

### 4. Added /api/llm_health Diagnostic Endpoint (main.py lines 730-835)

```python
@app.get("/api/llm_health")
async def llm_health() -> JSONResponse:
    """LLM health check - makes a minimal test call to verify OpenAI connectivity."""
```

Returns:
```json
{
  "ok": true/false,
  "final_url_used": "https://api.openai.com/v1/chat/completions",
  "status_code": 200,
  "error_type": null,
  "error_message": null,
  "response_preview": "..."
}
```

Or on error:
```json
{
  "ok": false,
  "error_type": "HTTP_ERROR",
  "error_message": "HTTP 401: ...",
  "final_url_used": "https://api.openai.com/v1/chat/completions",
  "status_code": 401,
  "response_preview": "{\"error\":{\"message\":\"Incorrect API key...\"}}"
}
```

## Railway Environment Variables

### Required
```bash
OPENAI_API_KEY=sk-proj-...
```

### Optional (Recommended)
```bash
OPENAI_BASE_URL=https://api.openai.com/v1
# OR
LLM_API_BASE=https://api.openai.com/v1
# OR just
LLM_API_BASE=https://api.openai.com  # Will be normalized to /v1
```

### Model Names
```bash
LLM_REASONING_MODEL=gpt-4
LLM_EXPRESSION_MODEL=gpt-4
# OR
LLM_REASONING_MODEL=gpt-3.5-turbo
LLM_EXPRESSION_MODEL=gpt-3.5-turbo
```

## Validation Checklist

### 1. Test /api/llm_health on Railway
```bash
curl https://your-backend.railway.app/api/llm_health
```

**Expected if configured correctly**:
```json
{
  "ok": true,
  "final_url_used": "https://api.openai.com/v1/chat/completions",
  "status_code": 200,
  "error_type": null,
  "error_message": null,
  "response_preview": "{'role': 'assistant', 'content': '...'}"
}
```

**If API key is wrong (401)**:
```json
{
  "ok": false,
  "error_type": "HTTP_ERROR",
  "error_message": "HTTP 401: ...",
  "final_url_used": "https://api.openai.com/v1/chat/completions",
  "status_code": 401,
  "response_preview": "{\"error\":{\"message\":\"Incorrect API key provided...\"}}"
}
```

**If model name is wrong (404)**:
```json
{
  "ok": false,
  "error_type": "HTTP_ERROR",
  "error_message": "HTTP 404: ...",
  "status_code": 404,
  "response_preview": "{\"error\":{\"message\":\"The model 'reasoning-model' does not exist\"}}"
}
```

### 2. Check Railway Logs

Look for these new log entries:

**On startup**:
```
INFO backend.app.llm_client Resolved api_key from OPENAI_API_KEY
INFO backend.app.llm_client Resolved api_base from OPENAI_BASE_URL
INFO backend.app.llm_client LLM config loaded {"api_base_domain":"api.openai.com",...}
INFO backend.app.main [LLM] Startup: LLM client initialized successfully
```

**On /api/chat request**:
```
INFO backend.app.llm_client [LLM] HTTP request {"url":"https://api.openai.com/v1/chat/completions","model":"gpt-4",...}
INFO backend.app.llm_client [LLM] HTTP response OK {"status_code":200,"model":"gpt-4"}
```

**On error (e.g., 401)**:
```
ERROR backend.app.llm_client [LLM] HTTP error {"url":"https://api.openai.com/v1/chat/completions","status_code":401,"response_preview":"{\"error\":{\"message\":\"Incorrect API key...\"}}"}
```

### 3. Test /api/chat

```bash
curl -X POST https://your-backend.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_text": "What is Bitcoin?"}'
```

**Expected**: Real LLM response (not fallback)
```json
{
  "action": "ANSWER",
  "rendered_text": "Bitcoin is a decentralized digital currency...",
  "has_output_text": true
}
```

**Not**: Fallback message
```json
{
  "action": "ANSWER",
  "rendered_text": "Governed response unavailable.",
  "failure_type": "PROVIDER_ERROR"
}
```

## Common Issues & Solutions

### Issue: "HTTP 401" in logs
**Cause**: Invalid or missing API key
**Solution**: Check `OPENAI_API_KEY` in Railway variables

### Issue: "HTTP 404" with "model does not exist"
**Cause**: Model name in `LLM_REASONING_MODEL` or `LLM_EXPRESSION_MODEL` doesn't exist
**Solution**: Use valid OpenAI model names:
- `gpt-4`
- `gpt-4-turbo-preview`
- `gpt-3.5-turbo`

### Issue: "HTTP 429" (rate limit)
**Cause**: Too many requests or quota exceeded
**Solution**: Check OpenAI dashboard for usage limits

### Issue: Timeout errors
**Cause**: Network issues or slow OpenAI response
**Solution**: Check Railway network connectivity, increase timeout in settings

### Issue: Connection errors
**Cause**: DNS or network issues
**Solution**: Check Railway can reach `api.openai.com`

## Files Changed

1. **backend/app/llm_client.py** (150 lines changed)
   - Added `_normalize_base_url()` helper (lines 41-62)
   - Applied normalization in `__init__` (line 140)
   - Fixed endpoint path to append `/chat/completions` (line 185)
   - Added detailed request logging (lines 200-209)
   - Added success logging (lines 217-223)
   - Split error handling into specific cases:
     - HTTP status errors with response preview (lines 252-274)
     - Timeout errors with URL and timeout value (lines 237-251)
     - Connection/DNS errors with error type (lines 275-289)

2. **backend/app/main.py** (108 lines added)
   - Added `get_shared_httpx_client` import (line 51)
   - Added `/api/llm_health` diagnostic endpoint (lines 730-835)

## Testing

✅ Compilation successful
✅ URL normalization tested
✅ Endpoint path fixed
✅ Error logging enhanced
✅ Health check endpoint added

## Expected Behavior

### Before Fix
- ❌ HTTP request to wrong URL (missing `/chat/completions`)
- ❌ Error message: "LLM adapter HTTP request failed" (no details)
- ❌ No status code, no response body, no URL in logs
- ❌ No way to diagnose OpenAI API issues

### After Fix
- ✅ HTTP request to correct URL: `https://api.openai.com/v1/chat/completions`
- ✅ URL normalization handles various input formats
- ✅ Detailed error messages with status codes and response previews
- ✅ Structured logs show exact URL, status, error type
- ✅ `/api/llm_health` endpoint for quick diagnostics
- ✅ No API keys logged (only domain and presence boolean)

## Ready to Deploy

All changes are backend-only. No frontend changes required.
