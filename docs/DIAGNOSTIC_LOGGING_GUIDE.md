# Diagnostic Logging Guide: Model Output Verification Failures

## Overview
Added comprehensive structured diagnostics to identify exactly why model output verification fails, without changing any behavior.

## What Was Added

### 1. Sanitize Preview Helper (`backend/mci_backend/diagnostic_utils.py`)
Safely sanitizes model output for logging:
- Removes markdown code fences (```json, ```)
- Collapses whitespace (newlines, tabs) to single spaces
- Truncates to 300 characters
- Never logs full user prompts or complete model outputs

**Tests**: `backend/tests/test_diagnostic_utils.py` (8 tests, all passing ✅)

### 2. Structured Diagnostic Logging (`backend/mci_backend/model_invocation_pipeline.py`)
When verification fails, logs a single-line JSON event with:

```json
{
  "event": "model_output_verification_failed",
  "request_id": "abc123...",
  "route": "/api/chat",
  "action": "ANSWER",
  "failure_type": "NON_JSON",
  "reason_code": "NON_JSON_RESPONSE",
  "parse_error": "Invalid JSON: ...",
  "has_output_json": false,
  "has_output_text": true,
  "output_shape": {
    "json_present": false,
    "text_present": true,
    "model_ok": true
  },
  "raw_preview": "Bitcoin is a decentralized digital currency that...",
  "model": "expression_model"
}
```

### 3. Deployment Marker (`backend/app/main.py`)
Logs build info at startup:

```json
{
  "event": "build_marker",
  "git_sha": "95868f5",
  "version": "2026.15.1",
  "timestamp": "2026-02-13T13:24:00.000000"
}
```

## How to Use in Production

### Grep for Verification Failures on Railway

```bash
# Find all verification failures
railway logs | grep "MODEL_VERIFY_FAIL"

# Extract just the JSON payload
railway logs | grep "MODEL_VERIFY_FAIL" | sed 's/.*MODEL_VERIFY_FAIL //'

# Filter by specific failure type
railway logs | grep "MODEL_VERIFY_FAIL" | grep "NON_JSON"

# Filter by action
railway logs | grep "MODEL_VERIFY_FAIL" | grep "ANSWER"

# Get the raw preview to see what the model returned
railway logs | grep "MODEL_VERIFY_FAIL" | jq '.raw_preview'
```

### Find Deployment Marker

```bash
# Get current deployment info
railway logs | grep "BUILD_MARKER"

# Extract git SHA
railway logs | grep "BUILD_MARKER" | jq '.git_sha'
```

### Common Failure Patterns

**Pattern 1: JSON Parse Failure**
```json
{
  "failure_type": "NON_JSON",
  "reason_code": "NON_JSON_RESPONSE",
  "has_output_text": true,
  "raw_preview": "Plain text answer without JSON structure"
}
```
→ Model returned plain text when JSON was expected

**Pattern 2: Empty Output**
```json
{
  "failure_type": "SCHEMA_MISMATCH",
  "reason_code": "EMPTY_OUTPUT",
  "has_output_text": false,
  "has_output_json": false
}
```
→ Model returned nothing

**Pattern 3: Schema Mismatch**
```json
{
  "failure_type": "SCHEMA_MISMATCH",
  "reason_code": "SCHEMA_MISMATCH",
  "parse_error": "Field 'answer_text' is required",
  "raw_preview": "{\"wrong_field\": \"value\"}"
}
```
→ Model returned JSON but with wrong structure

**Pattern 4: Forbidden Content**
```json
{
  "failure_type": "FORBIDDEN_CONTENT",
  "reason_code": "FORBIDDEN_PHRASE",
  "raw_preview": "I remember from our previous conversation..."
}
```
→ Model output contained forbidden phrases

## Log Locations

### Single-Line JSON (grep-friendly)
```
WARNING backend.mci_backend.model_invocation_pipeline MODEL_VERIFY_FAIL {"event":"model_output_verification_failed",...}
```

### Human-Readable (backward compatible)
```
WARNING backend.mci_backend.model_invocation_pipeline [FALLBACK] Model output verification failed, using fallback rendering
```

## Testing Locally

### Run Unit Tests
```bash
# Test sanitize_preview function
python -m pytest backend/tests/test_diagnostic_utils.py -v

# All tests should pass (8/8)
```

### Trigger Verification Failure Manually
```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# In another terminal, send a request
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -d '{"user_text":"Test question"}'

# Check logs for MODEL_VERIFY_FAIL
```

### Verify Log Output
Look for:
- ✅ `event=model_output_verification_failed`
- ✅ `failure_type` and `reason_code` present
- ✅ `raw_preview` sanitized (no newlines, max 300 chars)
- ✅ `user_text` NOT in logs (privacy)
- ✅ Single-line JSON format

## Files Changed

1. **`backend/mci_backend/diagnostic_utils.py`** (NEW)
   - `sanitize_preview()` helper function

2. **`backend/tests/test_diagnostic_utils.py`** (NEW)
   - 8 unit tests for sanitize_preview

3. **`backend/mci_backend/model_invocation_pipeline.py`** (lines 82-116)
   - Added structured diagnostic logging before fallback

4. **`backend/app/main.py`** (lines 113-140)
   - Added deployment marker log at startup

## Privacy & Security

✅ **Safe**:
- Raw preview limited to 300 chars
- Markdown fences removed
- Whitespace collapsed
- No full user prompts logged
- No sensitive data in logs

❌ **Never Logged**:
- Full user_text
- Complete model outputs
- API keys or secrets
- User identifiers (only hashed)

## Next Steps

After deploying to Railway:
1. Monitor logs for `MODEL_VERIFY_FAIL` events
2. Analyze failure patterns (failure_type, reason_code)
3. Check `raw_preview` to see what model is actually returning
4. Correlate with `git_sha` from BUILD_MARKER to track regressions
5. Use findings to fix root cause in verification logic (Step B - not done yet)

## Example Railway Log Analysis

```bash
# Get last 100 verification failures
railway logs --tail 100 | grep "MODEL_VERIFY_FAIL" > failures.log

# Count by failure type
cat failures.log | jq '.failure_type' | sort | uniq -c

# Most common reason codes
cat failures.log | jq '.reason_code' | sort | uniq -c

# Sample raw previews
cat failures.log | jq '.raw_preview' | head -10
```

This will tell you exactly why verification is failing in production.
