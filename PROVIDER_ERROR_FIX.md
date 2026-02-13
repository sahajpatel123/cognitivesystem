# Fix: PROVIDER_ERROR - NameError: name 'settings' is not defined

## Problem Identified
Production logs showed:
```json
{
  "action": "ANSWER",
  "failure_type": "PROVIDER_ERROR",
  "reason_code": "UNEXPECTED_ERROR",
  "parse_error": "name 'settings' is not defined",
  "model": "expression_model",
  "has_output_json": false,
  "has_output_text": false
}
```

The provider crashed **before** returning output due to a NameError.

## Root Cause

**File**: `backend/app/llm_client.py`
**Lines**: 204 (reasoning model) and 308 (expression model)

The code referenced `settings.llm_reasoning_model` and `settings.llm_expression_model` but:
- The file imports `get_settings` (line 10)
- In `__init__`, it calls `s = get_settings()` (line 59)
- But `s` is a local variable, not stored as instance attribute
- Lines 204 and 308 tried to use undefined global `settings`

## Why This Happened
1. **Import was correct** but never assigned to a module-level or instance variable
2. **Local variable `s`** was only used in `__init__` for extracting config values
3. **Model names** were needed later in `call_reasoning_model()` and `call_expression_model()`
4. **No reference** to the settings object was kept for those methods

## The Fix

### 1. Store Model Names in `__init__` (backend/app/llm_client.py)

**Lines 66-68** (NEW):
```python
# Store model names for use in call methods
self.reasoning_model_name = s.llm_reasoning_model
self.expression_model_name = s.llm_expression_model
```

### 2. Use Instance Attributes Instead of Undefined `settings`

**Line 207** (was 204):
```python
# OLD: "model": settings.llm_reasoning_model,
# NEW:
"model": self.reasoning_model_name,
```

**Line 311** (was 308):
```python
# OLD: "model": settings.llm_expression_model,
# NEW:
"model": self.expression_model_name,
```

### 3. Add Exception Logging (backend/mci_backend/model_runtime.py)

**Lines 178-185** (NEW):
```python
# Log full traceback for debugging provider errors
logger.exception(
    "PROVIDER_ERROR",
    extra={
        "model": "expression_model",
        "request_id": build_request_id(request),
        "route": "/api/chat",
    }
)
```

This ensures future provider errors include full traceback in Railway logs.

**Lines 10, 29** (NEW):
```python
import logging
logger = logging.getLogger(__name__)
```

## Exact Diffs

### backend/app/llm_client.py
```diff
@@ -63,6 +63,9 @@ class LLMClient:
         self.connect_timeout_seconds = connect_timeout_seconds or float(s.model_connect_timeout_seconds)
         self.request_id_header = request_id_header or s.request_id_header
         self.request_id_value = request_id_value
+        # Store model names for use in call methods
+        self.reasoning_model_name = s.llm_reasoning_model
+        self.expression_model_name = s.llm_expression_model
 
@@ -201,7 +204,7 @@ class LLMClient:
         }
 
         payload = {
-            "model": settings.llm_reasoning_model,
+            "model": self.reasoning_model_name,
             "messages": [
                 reasoning_instruction,
                 {"role": "user", "content": json.dumps(user_payload)},
@@ -305,7 +308,7 @@ class LLMClient:
         }
 
         payload = {
-            "model": settings.llm_expression_model,
+            "model": self.expression_model_name,
             "messages": [
                 expression_instruction,
                 {"role": "user", "content": json.dumps(user_payload)},
```

### backend/mci_backend/model_runtime.py
```diff
@@ -7,6 +7,7 @@ from __future__ import annotations
 
 import json
+import logging
 from typing import Any, Dict
 
@@ -25,6 +26,8 @@ from backend.mci_backend.model_contract import (
     validate_model_request,
 )
 
+logger = logging.getLogger(__name__)
+
 
 def _default_style() -> CognitiveStyle:
@@ -174,6 +177,15 @@ def invoke_model(request: ModelInvocationRequest, llm_client: LLMClient | None =
             message=str(exc),
         )
     except Exception as exc:  # noqa: BLE001
+        # Log full traceback for debugging provider errors
+        logger.exception(
+            "PROVIDER_ERROR",
+            extra={
+                "model": "expression_model",
+                "request_id": build_request_id(request),
+                "route": "/api/chat",
+            }
+        )
         return _failure_result(
             request,
             ModelFailureType.PROVIDER_ERROR,
```

## Why This Fix Works

1. **Model names stored once** during LLMClient initialization
2. **Instance attributes** accessible in all methods
3. **No dependency** on undefined global `settings`
4. **Minimal change** - only stores two strings, no redesign
5. **Future-proof** - logger.exception() will catch any similar errors with full traceback

## Validation

✅ **Compilation**: `python -m compileall` successful
✅ **Import test**: `from backend.app.llm_client import LLMClient` successful
✅ **Unit tests**: All diagnostic tests passing (8/8)

## Expected Production Behavior After Deploy

### Before Fix
```
MODEL_VERIFY_FAIL {
  "failure_type": "PROVIDER_ERROR",
  "parse_error": "name 'settings' is not defined",
  "has_output_text": false
}
```

### After Fix
```
# Normal successful response
{
  "ok": true,
  "has_output_text": true,
  "output_text": "Bitcoin is a decentralized digital currency..."
}
```

### If Future Provider Error Occurs
Railway logs will show:
```
ERROR backend.mci_backend.model_runtime PROVIDER_ERROR
Traceback (most recent call last):
  File "backend/mci_backend/model_runtime.py", line 121, in invoke_model
    raw_output = _call_expression_model(client, request)
  File "...", line X, in ...
    <exact line that failed>
<full exception details>
```

## Files Changed
1. `backend/app/llm_client.py` - Fixed NameError (3 lines added, 2 lines changed)
2. `backend/mci_backend/model_runtime.py` - Added exception logging (13 lines added)

## Ready to Deploy
All changes tested locally. No behavior changes except fixing the crash.
