# Step A Complete: High-Signal Diagnostics for Verification Failures

## What Was Done
Added structured diagnostics to identify exactly WHY model output verification fails in production.
**NO behavior changes** - fallback still occurs, only added logging.

## Files Changed

### 1. NEW: `backend/mci_backend/diagnostic_utils.py` (44 lines)
Helper function to sanitize model output for safe logging:
- Removes markdown fences (```json, ```)
- Collapses whitespace to single space
- Truncates to 300 chars
- Never logs full user prompts

### 2. NEW: `backend/tests/test_diagnostic_utils.py` (81 lines)
8 unit tests for sanitize_preview - **ALL PASSING ✅**

Run: `python -m pytest backend/tests/test_diagnostic_utils.py -v`

### 3. MODIFIED: `backend/mci_backend/model_invocation_pipeline.py`
**Lines 82-116**: Added structured diagnostic logging

**Before**:
```python
logger.warning(
    "[FALLBACK] Model output verification failed, using fallback rendering",
    extra={"request_id": ..., "model_ok": ..., ...}
)
```

**After**:
```python
diagnostic_payload = {
    "event": "model_output_verification_failed",
    "request_id": verified.request_id if verified else "unknown",
    "route": "/api/chat",
    "action": output_plan.action.value,
    "failure_type": verified.failure.failure_type.value,
    "reason_code": verified.failure.reason_code,
    "parse_error": verified.failure.message,
    "has_output_json": bool(result.output_json),
    "has_output_text": bool(result.output_text),
    "output_shape": {...},
    "raw_preview": sanitize_preview(result.output_text),
    "model": "expression_model",
}

# Single-line JSON for grep-friendly Railway logs
logger.warning("MODEL_VERIFY_FAIL %s", json.dumps(diagnostic_payload, ensure_ascii=False))

# Human-readable for backward compatibility
logger.warning("[FALLBACK] Model output verification failed...", extra=diagnostic_payload)
```

### 4. MODIFIED: `backend/app/main.py`
**Lines 113-140**: Added deployment marker at startup

```python
_git_sha = _get_git_sha()
logger.info(
    "BUILD_MARKER %s",
    json.dumps({
        "event": "build_marker",
        "git_sha": _git_sha,
        "version": APP_VERSION,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }, ensure_ascii=False)
)
```

### 5. NEW: `docs/DIAGNOSTIC_LOGGING_GUIDE.md`
Comprehensive guide for using diagnostics in production.

## How to Use on Railway

### Find Verification Failures
```bash
# All failures
railway logs | grep "MODEL_VERIFY_FAIL"

# Extract JSON only
railway logs | grep "MODEL_VERIFY_FAIL" | sed 's/.*MODEL_VERIFY_FAIL //'

# By failure type
railway logs | grep "MODEL_VERIFY_FAIL" | grep "NON_JSON"

# By action
railway logs | grep "MODEL_VERIFY_FAIL" | grep "ANSWER"

# See what model returned
railway logs | grep "MODEL_VERIFY_FAIL" | jq '.raw_preview'
```

### Find Deployment Info
```bash
railway logs | grep "BUILD_MARKER"
railway logs | grep "BUILD_MARKER" | jq '.git_sha'
```

## Example Log Output

### Verification Failure
```
WARNING backend.mci_backend.model_invocation_pipeline MODEL_VERIFY_FAIL {"event":"model_output_verification_failed","request_id":"abc123","route":"/api/chat","action":"ANSWER","failure_type":"NON_JSON","reason_code":"NON_JSON_RESPONSE","parse_error":"Invalid JSON: Expecting value","has_output_json":false,"has_output_text":true,"output_shape":{"json_present":false,"text_present":true,"model_ok":true},"raw_preview":"Bitcoin is a decentralized digital currency that operates without a central bank...","model":"expression_model"}
```

### Deployment Marker
```
INFO backend.app.main BUILD_MARKER {"event":"build_marker","git_sha":"95868f5","version":"2026.15.1","timestamp":"2026-02-13T13:24:00.000000"}
```

## Diagnostic Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Always "model_output_verification_failed" |
| `request_id` | string | Unique request ID for tracing |
| `route` | string | API endpoint (e.g., "/api/chat") |
| `action` | string | OutputAction enum (ANSWER, ASK_ONE_QUESTION, etc.) |
| `failure_type` | string | ModelFailureType enum (NON_JSON, SCHEMA_MISMATCH, etc.) |
| `reason_code` | string | Specific reason code |
| `parse_error` | string | Error message from parser/validator |
| `has_output_json` | boolean | Model returned JSON? |
| `has_output_text` | boolean | Model returned text? |
| `output_shape` | object | Detailed shape info |
| `raw_preview` | string | Sanitized preview (max 300 chars, no newlines) |
| `model` | string | Model identifier |

## Privacy & Security ✅

**Safe**:
- Preview limited to 300 chars
- Markdown fences removed
- Whitespace collapsed
- No full user prompts
- No sensitive data

**Never Logged**:
- Full user_text
- Complete model outputs
- API keys
- User identifiers

## Test Results

```bash
$ python -m pytest backend/tests/test_diagnostic_utils.py -v
collected 8 items

test_sanitize_preview_removes_json_fences PASSED         [ 12%]
test_sanitize_preview_removes_plain_fences PASSED        [ 25%]
test_sanitize_preview_collapses_whitespace PASSED        [ 37%]
test_sanitize_preview_truncates_long_text PASSED         [ 50%]
test_sanitize_preview_handles_empty_input PASSED         [ 62%]
test_sanitize_preview_strips_leading_trailing_whitespace PASSED [ 75%]
test_sanitize_preview_complex_example PASSED             [ 87%]
test_sanitize_preview_preserves_content_order PASSED     [100%]

8 passed in 1.55s ✅
```

## Next Steps

After deploying to Railway:

1. **Monitor logs** for `MODEL_VERIFY_FAIL` events
2. **Analyze patterns**: What failure_type and reason_code are most common?
3. **Check raw_preview**: What is the model actually returning?
4. **Correlate with git_sha**: Track regressions across deployments
5. **Use findings** to fix root cause (Step B - not done yet)

## Git Stats

```
 backend/app/main.py                              | 30 ++++++++++++++++++
 backend/mci_backend/diagnostic_utils.py          | 44 ++++++++++++++++++++++++
 backend/mci_backend/model_invocation_pipeline.py | 41 ++++++++++++++++------
 backend/tests/test_diagnostic_utils.py           | 81 ++++++++++++++++++++++++++++++++++++++++++
 docs/DIAGNOSTIC_LOGGING_GUIDE.md                 | 245 +++++++++++++++++++++++++++++++
 5 files changed, 441 insertions(+), 11 deletions(-)
```

## STOP - Step A Complete

✅ Sanitize preview helper added with tests
✅ Structured diagnostic logging added to pipeline
✅ Deployment marker added at startup
✅ Documentation created
✅ No behavior changes - fallback still occurs
✅ Privacy-safe logging (no user prompts, max 300 chars)

**Ready to commit and deploy to Railway for diagnosis.**
