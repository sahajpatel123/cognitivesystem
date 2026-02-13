# Fix: Model Output Verification - Accept Plain Text for ANSWER Actions

## Problem
Backend logs showed:
```
[LLM#2] Expression input
WARNING backend.mci_backend.model_invocation_pipeline [FALLBACK] Model output verification failed, using fallback rendering
```

The LLM was being invoked successfully, but the verification layer was rejecting the output and triggering fallback rendering, causing the UI to display "I apologize, but I'm unable to generate a response right now due to a technical issue" instead of the actual model answer.

## Root Cause
The verifier in `backend/mci_backend/model_output_verify.py` was **always attempting to parse JSON** for all actions, even when the model returned plain text for ANSWER actions. The logic was:

```python
# OLD CODE (line 202)
payload = model_result.output_json if model_result.output_json is not None else parse_model_json(model_result.output_text or "")
```

This caused `ModelFailureType.NON_JSON` errors when the model returned plain text answers like "Bitcoin is a decentralized digital currency..."

## Solution
Modified `verify_and_sanitize_model_output()` to support **both JSON and plain text** for ANSWER/REFUSE/CLOSE actions:

1. **If `output_json` is populated**: Use it directly (JSON path from model_runtime)
2. **If `output_text` is populated**: Try JSON parse first for backward compatibility
3. **If JSON parse fails for ANSWER/REFUSE/CLOSE**: Accept as plain text and perform semantic checks
4. **If JSON parse fails for ASK_ONE_QUESTION**: Reject (JSON required)

### Key Changes

**File**: `backend/mci_backend/model_output_verify.py`

```python
# NEW CODE (lines 201-253)
# CRITICAL FIX: Support both JSON and plain text for ANSWER/REFUSE/CLOSE
if model_result.output_json is not None:
    payload = model_result.output_json
elif model_result.output_text:
    try:
        payload = parse_model_json(model_result.output_text)
    except ModelOutputParseError:
        # JSON parse failed - for ANSWER/REFUSE/CLOSE, accept as plain text
        if output_plan.action in {OutputAction.ANSWER, OutputAction.REFUSE, OutputAction.CLOSE}:
            raw_text = model_result.output_text
            sanitized = _sanitize_text(raw_text)
            
            if not sanitized:
                return _failure(request_id, ModelFailureType.SCHEMA_MISMATCH, "EMPTY_OUTPUT", "Model returned empty text")
            
            # Perform semantic checks on plain text
            failure = _check_forbidden_phrases(sanitized, request_id)
            if failure:
                return failure
            
            # Check unknown disclosure for ANSWER
            if output_plan.action == OutputAction.ANSWER and output_plan.unknown_disclosure != UnknownDisclosureMode.NONE:
                # ... validation logic ...
            
            return ModelInvocationResult(
                request_id=request_id,
                ok=True,
                output_text=sanitized,
                output_json=None,
                failure=None,
            )
```

## Verification

### Tests Updated
- `backend/tests/test_phase12_model_output_verify.py`:
  - `test_non_json_fails` → Now expects plain text to **pass** for ANSWER
  - `test_markdown_fence_fails` → Now expects plain text with markdown to **pass** for ANSWER
  - All 10 tests passing ✅

### Expected Behavior
1. **JSON format**: Model returns `{"answer_text": "..."}` → Parsed and validated as before
2. **Plain text format**: Model returns `"Bitcoin is a decentralized..."` → Accepted and sanitized
3. **Empty text**: Model returns `""` → Rejected with `EMPTY_OUTPUT`
4. **Forbidden phrases**: Detected in both JSON and plain text paths
5. **Unknown disclosure**: Enforced in both JSON and plain text paths

## Impact
- **ANSWER actions**: Now accept both JSON (`{"answer_text": "..."}`) and plain text
- **REFUSE actions**: Now accept both JSON (`{"refusal_text": "..."}`) and plain text
- **CLOSE actions**: Now accept both JSON (`{"closure_text": "..."}`) and plain text
- **ASK_ONE_QUESTION**: Still requires JSON (no change)

## Testing
```bash
# Run verification tests
python -m pytest backend/tests/test_phase12_model_output_verify.py -v

# Run regression tests
python -m pytest backend/tests/test_regression_meta_scaffolding.py -v

# Test with curl (after starting backend)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -d '{"user_text":"What is Bitcoin?"}'
```

## Files Changed
1. `backend/mci_backend/model_output_verify.py` - Core fix (lines 201-317)
2. `backend/tests/test_phase12_model_output_verify.py` - Updated test expectations

## Acceptance Criteria ✅
- [x] Model output verification accepts plain text for ANSWER actions
- [x] Verification still accepts JSON format for backward compatibility
- [x] Semantic checks (forbidden phrases, unknown disclosure) work for both formats
- [x] Empty text is rejected appropriately
- [x] Existing tests updated and passing
- [ ] Manual curl test confirms real answers (not fallback) are returned
- [ ] Railway deployment shows no "[FALLBACK] Model output verification failed" warnings
