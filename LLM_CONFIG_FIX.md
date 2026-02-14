# Fix: LLM Configuration Missing (api_base / api_key)

## Problem Identified
Production Railway logs showed:
```
RuntimeError: LLM configuration missing (api_base / api_key)
from backend/app/llm_client.py line 72 in _post()
```

The LLMClient was unable to find api_base and api_key configuration values.

## Root Cause

**File**: `backend/app/llm_client.py` line 60-61 (old code)

The configuration resolution was too fragile:
```python
self.api_base = api_base or s.model_base_url or s.model_provider_base_url or s.llm_api_base
self.api_key = api_key or s.model_api_key or s.llm_api_key
```

**Issues**:
1. Only checked Pydantic settings fields (which may not be populated from env vars)
2. No direct env var fallback if settings fields were None
3. No validation or helpful error messages listing which vars were checked
4. No logging to debug which config source was used

## The Fix

### 1. Added Robust Env Var Resolution Functions

**Lines 41-89** (NEW):

```python
def _resolve_api_base() -> Optional[str]:
    """Resolve API base URL from env vars with fallbacks."""
    # Try env vars in priority order
    for env_var in ["LLM_API_BASE", "MODEL_BASE_URL", "MODEL_PROVIDER_BASE_URL", "API_BASE", "OPENAI_BASE_URL"]:
        value = os.getenv(env_var)
        if value:
            logger.info(f"Resolved api_base from {env_var}")
            return value
    
    # Check if provider suggests OpenAI
    provider = os.getenv("MODEL_PROVIDER", "").lower()
    if "openai" in provider:
        logger.info("Defaulting to OpenAI base URL based on provider")
        return "https://api.openai.com/v1/chat/completions"
    
    return None


def _resolve_api_key() -> Optional[str]:
    """Resolve API key from env vars with fallbacks."""
    for env_var in ["LLM_API_KEY", "MODEL_API_KEY", "API_KEY", "OPENAI_API_KEY"]:
        value = os.getenv(env_var)
        if value:
            logger.info(f"Resolved api_key from {env_var}")
            return value
    
    return None
```

### 2. Enhanced __init__ with Validation and Logging

**Lines 113-144** (MODIFIED):

```python
# Robust config resolution: try passed params, then settings, then env vars
self.api_base = api_base or s.model_base_url or s.model_provider_base_url or s.llm_api_base or _resolve_api_base()
self.api_key = api_key or s.model_api_key or s.llm_api_key or _resolve_api_key()

# Validate and log config (safe - no secrets)
if not self.api_base:
    checked_vars = "LLM_API_BASE, MODEL_BASE_URL, MODEL_PROVIDER_BASE_URL, API_BASE, OPENAI_BASE_URL"
    raise RuntimeError(
        f"LLM api_base not configured. Checked env vars: {checked_vars}. "
        "Set one of these environment variables with your LLM provider's base URL."
    )

if not self.api_key:
    checked_vars = "LLM_API_KEY, MODEL_API_KEY, API_KEY, OPENAI_API_KEY"
    raise RuntimeError(
        f"LLM api_key not configured. Checked env vars: {checked_vars}. "
        "Set one of these environment variables with your LLM provider's API key."
    )

# Extract domain for safe logging (no secrets)
api_base_domain = self.api_base.split("//")[-1].split("/")[0] if "//" in self.api_base else self.api_base.split("/")[0]

logger.info(
    "LLM config loaded",
    extra={
        "api_base_domain": api_base_domain,
        "api_key_present": bool(self.api_key),
        "provider": s.model_provider,
        "reasoning_model": s.llm_reasoning_model,
        "expression_model": s.llm_expression_model,
    }
)
```

## Environment Variables

### For OpenAI (Priority Order)

**API Base URL** (checked in order):
1. `LLM_API_BASE` - Preferred
2. `MODEL_BASE_URL` - Alternative
3. `MODEL_PROVIDER_BASE_URL` - Alternative
4. `API_BASE` - Generic fallback
5. `OPENAI_BASE_URL` - OpenAI-specific
6. Auto-default to `https://api.openai.com/v1/chat/completions` if `MODEL_PROVIDER` contains "openai"

**API Key** (checked in order):
1. `LLM_API_KEY` - Preferred
2. `MODEL_API_KEY` - Alternative
3. `API_KEY` - Generic fallback
4. `OPENAI_API_KEY` - OpenAI-specific

### For Custom Provider

**API Base URL**: Set any of the above (preferably `LLM_API_BASE`)
**API Key**: Set any of the above (preferably `LLM_API_KEY`)

### Example Railway Configuration

#### OpenAI
```bash
LLM_API_KEY=sk-proj-...
LLM_API_BASE=https://api.openai.com/v1/chat/completions
MODEL_PROVIDER=openai
LLM_REASONING_MODEL=gpt-4
LLM_EXPRESSION_MODEL=gpt-4
```

#### Custom Provider (e.g., Azure, Anthropic)
```bash
LLM_API_KEY=your-api-key
LLM_API_BASE=https://your-provider.com/v1/chat/completions
MODEL_PROVIDER=custom
LLM_REASONING_MODEL=your-model-name
LLM_EXPRESSION_MODEL=your-model-name
```

## Verification Commands

### Check Railway Environment Variables
```bash
# In Railway shell or logs
railway run printenv | grep -E "LLM_|MODEL_|API_"
```

### Check Startup Logs
Look for this log entry when backend starts:
```
INFO backend.app.llm_client LLM config loaded
{
  "api_base_domain": "api.openai.com",
  "api_key_present": true,
  "provider": "openai",
  "reasoning_model": "gpt-4",
  "expression_model": "gpt-4"
}
```

Also look for resolution logs:
```
INFO backend.app.llm_client Resolved api_base from LLM_API_BASE
INFO backend.app.llm_client Resolved api_key from LLM_API_KEY
```

### If Configuration Fails
You'll see a clear error message:
```
RuntimeError: LLM api_base not configured. Checked env vars: LLM_API_BASE, MODEL_BASE_URL, MODEL_PROVIDER_BASE_URL, API_BASE, OPENAI_BASE_URL. Set one of these environment variables with your LLM provider's base URL.
```

or

```
RuntimeError: LLM api_key not configured. Checked env vars: LLM_API_KEY, MODEL_API_KEY, API_KEY, OPENAI_API_KEY. Set one of these environment variables with your LLM provider's API key.
```

## Exact Diff

```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 import json
 import logging
+import os
 import re
 from typing import Any, Dict, Union, Optional
 
@@ -36,6 +37,50 @@ from .schemas import (
 
 logger = logging.getLogger(__name__)
 
+
+def _resolve_api_base() -> Optional[str]:
+    """Resolve API base URL from env vars with fallbacks."""
+    # Try env vars in priority order
+    for env_var in ["LLM_API_BASE", "MODEL_BASE_URL", "MODEL_PROVIDER_BASE_URL", "API_BASE", "OPENAI_BASE_URL"]:
+        value = os.getenv(env_var)
+        if value:
+            logger.info(f"Resolved api_base from {env_var}")
+            return value
+    
+    # Check if provider suggests OpenAI
+    provider = os.getenv("MODEL_PROVIDER", "").lower()
+    if "openai" in provider:
+        logger.info("Defaulting to OpenAI base URL based on provider")
+        return "https://api.openai.com/v1/chat/completions"
+    
+    return None
+
+
+def _resolve_api_key() -> Optional[str]:
+    """Resolve API key from env vars with fallbacks."""
+    for env_var in ["LLM_API_KEY", "MODEL_API_KEY", "API_KEY", "OPENAI_API_KEY"]:
+        value = os.getenv(env_var)
+        if value:
+            logger.info(f"Resolved api_key from {env_var}")
+            return value
+    
+    return None
+
 
 class LLMClient:
     """Model-agnostic HTTP client for the reasoning and expression models.
@@ -58,8 +103,35 @@ class LLMClient:
         request_id_value: Optional[str] = None,
     ) -> None:
         s = get_settings()
-        self.api_base = api_base or s.model_base_url or s.model_provider_base_url or s.llm_api_base
-        self.api_key = api_key or s.model_api_key or s.llm_api_key
+        
+        # Robust config resolution: try passed params, then settings, then env vars
+        self.api_base = api_base or s.model_base_url or s.model_provider_base_url or s.llm_api_base or _resolve_api_base()
+        self.api_key = api_key or s.model_api_key or s.llm_api_key or _resolve_api_key()
+        
+        # Validate and log config (safe - no secrets)
+        if not self.api_base:
+            checked_vars = "LLM_API_BASE, MODEL_BASE_URL, MODEL_PROVIDER_BASE_URL, API_BASE, OPENAI_BASE_URL"
+            raise RuntimeError(
+                f"LLM api_base not configured. Checked env vars: {checked_vars}. "
+                "Set one of these environment variables with your LLM provider's base URL."
+            )
+        
+        if not self.api_key:
+            checked_vars = "LLM_API_KEY, MODEL_API_KEY, API_KEY, OPENAI_API_KEY"
+            raise RuntimeError(
+                f"LLM api_key not configured. Checked env vars: {checked_vars}. "
+                "Set one of these environment variables with your LLM provider's API key."
+            )
+        
+        # Extract domain for safe logging (no secrets)
+        api_base_domain = self.api_base.split("//")[-1].split("/")[0] if "//" in self.api_base else self.api_base.split("/")[0]
+        
+        logger.info(
+            "LLM config loaded",
+            extra={
+                "api_base_domain": api_base_domain,
+                "api_key_present": bool(self.api_key),
+                "provider": s.model_provider,
+                "reasoning_model": s.llm_reasoning_model,
+                "expression_model": s.llm_expression_model,
+            }
+        )
+        
         self.timeout_seconds = timeout_seconds or float(s.model_timeout_seconds)
         self.connect_timeout_seconds = connect_timeout_seconds or float(s.model_connect_timeout_seconds)
```

## Why This Works

1. **Multiple fallback layers**: Passed params → Settings fields → Direct env vars
2. **Clear error messages**: Lists exactly which env vars were checked
3. **Safe logging**: Logs domain only (no API keys), confirms key is present
4. **Provider-aware**: Auto-defaults to OpenAI URL if provider is "openai"
5. **Validation at init**: Fails fast with helpful message instead of crashing later in `_post()`

## Files Changed
- `backend/app/llm_client.py` - 87 lines added (resolution functions + validation + logging)

## Testing

✅ Compilation successful
✅ Config resolution tested with env vars
✅ Safe logging (no secrets exposed)

## Expected Production Behavior

**Before**: `RuntimeError: LLM configuration missing (api_base / api_key)` at line 72

**After**: 
- If env vars set: LLM calls succeed with proper config
- If env vars missing: Clear error message listing which vars to set
- Startup logs show: `LLM config loaded` with domain and key presence

**Ready to deploy to Railway.**
