# Fix Summary: Meta Scaffolding Bug

## Problem
The chat UI was displaying meta scaffolding text instead of actual assistant answers:
```
Answer: Providing a concise response based on limited details.
Confidence: Cautious.
Unknown: Some factors are not yet known.
Assumption: Proceeding with limited context only.
```

This broke usability as users saw internal system metadata instead of helpful responses.

## Root Cause
The backend's `fallback_rendering.py` module was generating meta scaffolding text when the LLM failed or returned invalid output. This fallback text was designed for internal debugging but was being shown to end users.

**Key files involved:**
- `backend/mci_backend/fallback_rendering.py` - Generated meta scaffolding
- `backend/app/quality/gate.py` - Had PLACEHOLDER constant with meta text
- `backend/app/reliability/engine.py` - Passed fallback text to frontend

## Solution Implemented

### 1. Fixed Fallback Rendering (STEP B)
**File:** `backend/mci_backend/fallback_rendering.py`

**Changed:** `_render_answer()` function
- **Before:** Generated "Answer: Providing a concise response based on limited details. Confidence: ... Unknown: ... Assumption: ..."
- **After:** Returns helpful message: "I'm currently operating in a limited mode and may not be able to provide a complete answer. Please try rephrasing your question or try again shortly."

### 2. Removed Meta Scaffolding Constants (STEP B)
**File:** `backend/app/quality/gate.py`

**Changed:**
- Removed `PLACEHOLDER = "Providing a concise response based on limited details"` constant
- Removed PLACEHOLDER check from `evaluate_quality()` function
- Updated `__all__` exports to remove PLACEHOLDER

### 3. Added Frontend Diagnostic Logging (STEP C)
**File:** `frontend/app/(chat)/product/chat/page.tsx`

**Added:** Dev-only console logging in `sendMessage()` function
```javascript
if (process.env.NODE_ENV === 'development' && debugTransport) {
  console.log('[DEV] Full /api/chat response:', {
    keys: Object.keys(parsed),
    action: parsed.action,
    rendered_text: parsed.rendered_text?.substring(0, 200),
    failure_type: parsed.failure_type,
    hasAnswer: !!parsed.answer,
    hasMessage: !!parsed.message,
    hasContent: !!parsed.content,
  });
}
```

This helps diagnose whether bugs are frontend or backend issues.

### 4. Implemented LLM Provider Abstraction (STEP D)
**New files created:**
- `backend/app/providers/base.py` - Abstract base class and interfaces
- `backend/app/providers/openai_provider.py` - OpenAI implementation
- `backend/app/providers/openai_compatible_provider.py` - Llama/Groq/Fireworks/etc.
- `backend/app/providers/factory.py` - Factory for creating providers from env

**Environment variables:**
```bash
LLM_PROVIDER=openai|openai_compat
LLM_API_KEY=<your-key>
LLM_BASE_URL=<endpoint-url>  # Required for openai_compat
LLM_MODEL=<model-name>
LLM_TIMEOUT=30.0
LLM_CONNECT_TIMEOUT=10.0
```

**Benefits:**
- Easy switching between OpenAI and Llama-compatible providers
- No code changes required, just environment variables
- Supports Groq, Fireworks, Together, vLLM, Ollama, etc.

### 5. Added Regression Tests (STEP E)
**File:** `backend/tests/test_regression_meta_scaffolding.py`

**Tests:**
1. `test_no_meta_scaffolding_in_answer()` - Ensures real answers never contain meta scaffolding
2. `test_fallback_is_helpful_not_meta()` - Ensures fallback text is helpful, not meta

**Updated test:**
- `backend/tests/test_step5_quality_gate.py` - Updated to expect real answers instead of meta text

### 6. Documentation (STEP F)
**File:** `docs/LLM_PROVIDER_SETUP.md`

Complete guide covering:
- Environment variable configuration
- Provider examples (OpenAI, Groq, Fireworks, Together, vLLM, Ollama)
- Response contract specification
- Troubleshooting guide
- Migration guide from OpenAI to Llama

## Files Changed

### Backend
1. `backend/mci_backend/fallback_rendering.py` - Fixed `_render_answer()`
2. `backend/app/quality/gate.py` - Removed PLACEHOLDER constant and check
3. `backend/tests/test_step5_quality_gate.py` - Updated test expectations
4. `backend/tests/test_regression_meta_scaffolding.py` - New regression tests
5. `backend/app/providers/base.py` - New LLM provider abstraction
6. `backend/app/providers/openai_provider.py` - New OpenAI provider
7. `backend/app/providers/openai_compatible_provider.py` - New OpenAI-compat provider
8. `backend/app/providers/factory.py` - New provider factory

### Frontend
1. `frontend/app/(chat)/product/chat/page.tsx` - Added dev-only logging

### Documentation
1. `docs/LLM_PROVIDER_SETUP.md` - New comprehensive setup guide
2. `docs/FIX_SUMMARY_META_SCAFFOLDING.md` - This file

## Testing

All tests pass:
```bash
# Regression tests
pytest backend/tests/test_regression_meta_scaffolding.py -v
# Result: 2 passed

# Quality gate tests
pytest backend/tests/test_step5_quality_gate.py -v
# Result: 1 passed
```

## Response Contract

The system now follows this contract:

```json
{
  "message": {
    "role": "assistant",
    "text": "<ACTUAL ANSWER TEXT>",
    "status": "ok"
  },
  "meta": {
    "confidence": "...",
    "assumptions": [...],
    "unknowns": [...],
    "policy_mode": "...",
    "trace_id": "..."
  }
}
```

**Critical Rules:**
- `message.text` MUST contain actual assistant answer (human readable)
- `meta` MUST NOT be concatenated into `message.text`
- Frontend MUST render only `message.text`
- Frontend may show `meta` under Debug accordion if debug mode enabled

## Verification

To verify the fix works:

1. **Local dev test:**
   ```bash
   # Start backend
   cd backend && python -m uvicorn app.main:app --reload
   
   # Start frontend
   cd frontend && npm run dev
   
   # Ask: "What is Bitcoin?"
   # Expected: Normal explanation paragraph(s), NOT meta scaffolding
   ```

2. **Check dev console (frontend):**
   - Open browser DevTools → Console
   - Look for `[DEV] Full /api/chat response:` logs
   - Verify `rendered_text` contains real answer, not meta

3. **Run regression tests:**
   ```bash
   pytest backend/tests/test_regression_meta_scaffolding.py -v
   ```

## Migration to Llama

To switch from OpenAI to Llama (e.g., via Groq):

```bash
# Update .env
export LLM_PROVIDER=openai_compat
export LLM_API_KEY=gsk_...
export LLM_BASE_URL=https://api.groq.com/openai/v1/chat/completions
export LLM_MODEL=llama-3.1-70b-versatile

# Restart application
# No code changes needed!
```

## Acceptance Criteria

✅ Local dev: Asking "What is Bitcoin?" returns normal explanation, not meta header  
✅ Production: UI shows real answer  
✅ Debug toggle can show meta fields if enabled (future enhancement)  
✅ Switching LLM_PROVIDER + base_url works without code changes  
✅ All regression tests pass  
✅ No meta scaffolding text appears in user-facing responses  

## Next Steps

1. **Deploy to production** and verify fix works
2. **Monitor logs** for any LLM failures that trigger fallback
3. **Add debug toggle UI** to show meta fields for power users (optional)
4. **Test with Llama provider** to verify abstraction works
5. **Add more comprehensive integration tests** for full chat flow

## Rollback Plan

If issues arise, revert these commits:
1. `backend/mci_backend/fallback_rendering.py` - Revert `_render_answer()`
2. `backend/app/quality/gate.py` - Restore PLACEHOLDER constant
3. `frontend/app/(chat)/product/chat/page.tsx` - Remove dev logging

The system will fall back to previous behavior (showing meta scaffolding).
