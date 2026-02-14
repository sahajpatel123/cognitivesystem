# Fix: Railway Startup Crash + OpenAI LLM Configuration

## Problem
Railway backend was crashing at boot with:
```
RuntimeError: LLM api_base not configured. Checked env vars: ...
```

**Root Cause**: `ConversationService()` was instantiated at module import time (line 188 in `main.py`), which called `LLMClient()` in its `__init__`. If env vars were missing, the RuntimeError crashed Uvicorn before the server could start.

## Solution Overview

1. **Added OpenAI-specific env var support** (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_KEY)
2. **Removed import-time LLM initialization** - moved to startup event
3. **Added graceful degradation** - server starts even if LLM config missing
4. **Added health/readiness endpoints** - /healthz (always 200), /readyz (200 if LLM ok, 503 if not)
5. **Added request-time 503 guard** - /api/chat returns clear error if LLM not configured

## Changes Made

### 1. backend/app/llm_client.py

**Added OpenAI env var priority**:
- API Base: `LLM_API_BASE` → **`OPENAI_BASE_URL`** → `MODEL_BASE_URL` → `MODEL_PROVIDER_BASE_URL` → `API_BASE`
- API Key: **`OPENAI_API_KEY`** → `LLM_API_KEY` → `MODEL_API_KEY` → **`OPENAI_KEY`** → `API_KEY`
- Auto-default to `https://api.openai.com/v1` if `MODEL_PROVIDER` contains "openai"

**Lines changed**: 56, 66, 84, 120, 127

### 2. backend/app/service.py

**Made ConversationService accept optional LLMClient**:
```python
def __init__(self, llm_client: LLMClient | None = None) -> None:
    self.llm = llm_client
```

This prevents import-time LLM instantiation.

**Lines changed**: 32-38

### 3. backend/app/main.py

**A) Removed import-time crash** (line 188-189):
```python
# OLD: service = ConversationService()
# NEW:
service = ConversationService(llm_client=None)
```

**B) Added startup event** (lines 193-211):
```python
@app.on_event("startup")
async def startup_event():
    """Initialize LLM client on startup. Never crash - store error if config missing."""
    try:
        llm_client = LLMClient()
        service.llm = llm_client
        app.state.llm_ok = True
        app.state.llm_client = llm_client
        app.state.llm_error = None
        logger.info("[LLM] Startup: LLM client initialized successfully")
    except Exception as exc:
        # Store error but don't crash - allow server to start
        app.state.llm_ok = False
        app.state.llm_client = None
        app.state.llm_error = str(exc)
        logger.warning(
            "[LLM] Startup: LLM client initialization failed - server will return 503 for /api/chat",
            extra={"error": str(exc), "error_type": type(exc).__name__}
        )
```

**C) Added /healthz endpoint** (lines 700-703):
```python
@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Health check endpoint - always returns 200 if server is running."""
    return JSONResponse(status_code=200, content={"ok": True})
```

**D) Added /readyz endpoint** (lines 706-727):
```python
@app.get("/readyz")
async def readyz() -> JSONResponse:
    """Readiness check endpoint - returns 200 if LLM is configured, 503 otherwise."""
    llm_ok = getattr(app.state, "llm_ok", False)
    if llm_ok:
        settings = get_settings()
        return JSONResponse(
            status_code=200,
            content={
                "ready": True,
                "provider": settings.model_provider,
            }
        )
    else:
        llm_error = getattr(app.state, "llm_error", "LLM not initialized")
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "error": llm_error,
            }
        )
```

**E) Added 503 guard in /api/chat** (lines 743-755):
```python
# Check LLM readiness before processing
if not getattr(request.app.state, "llm_ok", False):
    llm_error = getattr(request.app.state, "llm_error", "LLM not configured")
    return JSONResponse(
        status_code=503,
        content={
            "error": "LLM_NOT_CONFIGURED",
            "message": "LLM provider base URL / API key not configured in environment variables.",
            "required": ["LLM_API_BASE=https://api.openai.com/v1", "OPENAI_API_KEY=***"],
            "checked_envs": ["LLM_API_BASE", "OPENAI_BASE_URL", "MODEL_BASE_URL", "MODEL_PROVIDER_BASE_URL", "API_BASE", "OPENAI_API_KEY", "LLM_API_KEY", "MODEL_API_KEY", "OPENAI_KEY", "API_KEY"],
            "detail": llm_error,
        }
    )
```

## Environment Variables Supported

### For OpenAI (Recommended)

**API Base URL** (checked in priority order):
1. `LLM_API_BASE` - Generic (preferred)
2. **`OPENAI_BASE_URL`** - OpenAI-specific ⭐
3. `MODEL_BASE_URL` - Alternative
4. `MODEL_PROVIDER_BASE_URL` - Alternative
5. `API_BASE` - Generic fallback
6. Auto-default if `MODEL_PROVIDER=openai`

**API Key** (checked in priority order):
1. **`OPENAI_API_KEY`** - OpenAI-specific (preferred) ⭐
2. `LLM_API_KEY` - Generic
3. `MODEL_API_KEY` - Alternative
4. **`OPENAI_KEY`** - OpenAI alternative ⭐
5. `API_KEY` - Generic fallback

### Railway Configuration Examples

#### Option 1: OpenAI-specific vars (Recommended)
```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_PROVIDER=openai
LLM_REASONING_MODEL=gpt-4
LLM_EXPRESSION_MODEL=gpt-4
```

#### Option 2: Generic vars
```bash
LLM_API_KEY=sk-proj-...
LLM_API_BASE=https://api.openai.com/v1
MODEL_PROVIDER=openai
LLM_REASONING_MODEL=gpt-4
LLM_EXPRESSION_MODEL=gpt-4
```

#### Option 3: Minimal (with auto-default)
```bash
OPENAI_API_KEY=sk-proj-...
MODEL_PROVIDER=openai
LLM_REASONING_MODEL=gpt-4
LLM_EXPRESSION_MODEL=gpt-4
```
(Base URL auto-defaults to `https://api.openai.com/v1`)

## Railway Deploy Checklist

### 1. Set Environment Variables
In Railway → Backend Service → Variables:

**Required**:
- `OPENAI_API_KEY` = `sk-proj-...` (your OpenAI API key)

**Optional** (recommended):
- `OPENAI_BASE_URL` = `https://api.openai.com/v1`
- `MODEL_PROVIDER` = `openai`
- `LLM_REASONING_MODEL` = `gpt-4` (or `gpt-3.5-turbo`)
- `LLM_EXPRESSION_MODEL` = `gpt-4` (or `gpt-3.5-turbo`)

### 2. Redeploy
Click "Deploy" in Railway or push to trigger auto-deploy.

### 3. Verify Startup Logs
Look for one of these in Railway logs:

**Success**:
```
INFO backend.app.llm_client Resolved api_key from OPENAI_API_KEY
INFO backend.app.llm_client Resolved api_base from OPENAI_BASE_URL
INFO backend.app.llm_client LLM config loaded {"api_base_domain":"api.openai.com","api_key_present":true,...}
INFO backend.app.main [LLM] Startup: LLM client initialized successfully
```

**Failure (but server still starts)**:
```
WARNING backend.app.main [LLM] Startup: LLM client initialization failed - server will return 503 for /api/chat
```

### 4. Test Endpoints

**A) Health check (always works)**:
```bash
curl https://your-backend.railway.app/healthz
# Expected: {"ok": true}
```

**B) Readiness check**:
```bash
curl https://your-backend.railway.app/readyz
# If configured: {"ready": true, "provider": "openai"}
# If not: {"ready": false, "error": "..."}
```

**C) Chat endpoint**:
```bash
curl -X POST https://your-backend.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_text": "What is Bitcoin?"}'

# If configured: Real LLM response
# If not: 503 with clear error message
```

## Expected Behavior

### Before Fix
- ❌ Server crashes at import time if env vars missing
- ❌ Uvicorn never starts
- ❌ No way to diagnose issue

### After Fix
- ✅ Server always starts (even without env vars)
- ✅ `/healthz` returns 200 (server is alive)
- ✅ `/readyz` returns 503 if LLM not configured (clear status)
- ✅ `/api/chat` returns 503 with helpful error listing required env vars
- ✅ Logs show exactly which env var was used or what's missing
- ✅ No secrets logged (only domain and key_present boolean)

## Verification Commands

### Check Railway Environment Variables
```bash
railway run printenv | grep -E "OPENAI|LLM|MODEL|API"
```

### Check Startup Logs
```bash
railway logs | grep -E "LLM|api_base|api_key"
```

### Test Locally Without Env Vars
```bash
# Unset all LLM env vars
unset OPENAI_API_KEY LLM_API_KEY MODEL_API_KEY
unset OPENAI_BASE_URL LLM_API_BASE MODEL_BASE_URL

# Start server - should NOT crash
uvicorn backend.app.main:app --reload

# Test endpoints
curl http://localhost:8000/healthz  # Should return 200
curl http://localhost:8000/readyz   # Should return 503
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_text":"test"}'  # Should return 503 with clear error
```

## Files Changed

1. **backend/app/llm_client.py** - 8 lines changed
   - Prioritized OpenAI env vars (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_KEY)
   - Updated error messages to list OpenAI vars first

2. **backend/app/service.py** - 7 lines changed
   - Made LLMClient optional in ConversationService.__init__

3. **backend/app/main.py** - 59 lines added
   - Removed import-time service instantiation
   - Added startup event with safe LLM initialization
   - Added /healthz endpoint
   - Added /readyz endpoint
   - Added 503 guard in /api/chat

## Security

✅ **No secrets logged**:
- Only logs `api_base_domain` (e.g., "api.openai.com")
- Only logs `api_key_present` (true/false)
- Never logs actual API keys

✅ **Error messages sanitized**:
- Lists which env vars were checked
- Does not expose actual values

## Testing

✅ Compilation successful
✅ Import works without env vars (no crash)
✅ Service created with llm=None
✅ All code changes verified

## Ready to Deploy

All changes are backend-only. No frontend changes required.
