# LLM Provider Setup Guide

This guide explains how to configure the LLM provider for the cognitive system.

## Overview

The system supports multiple LLM providers through a unified abstraction layer:
- **OpenAI** (default)
- **OpenAI-compatible** providers (Llama via vLLM, Groq, Fireworks, Together, etc.)

## Environment Variables

Configure the LLM provider using these environment variables:

### Required
- `LLM_API_KEY` - API key for your chosen provider

### Optional
- `LLM_PROVIDER` - Provider type: `openai` (default) or `openai_compat`
- `LLM_BASE_URL` - Base URL for API endpoint (required for `openai_compat`)
- `LLM_MODEL` - Model name (default: `gpt-4`)
- `LLM_TIMEOUT` - Request timeout in seconds (default: `30.0`)
- `LLM_CONNECT_TIMEOUT` - Connection timeout in seconds (default: `10.0`)

## Configuration Examples

### OpenAI (Default)

```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-4
```

### Groq (Llama 3)

```bash
export LLM_PROVIDER=openai_compat
export LLM_API_KEY=gsk_...
export LLM_BASE_URL=https://api.groq.com/openai/v1/chat/completions
export LLM_MODEL=llama-3.1-70b-versatile
```

### Fireworks AI

```bash
export LLM_PROVIDER=openai_compat
export LLM_API_KEY=fw_...
export LLM_BASE_URL=https://api.fireworks.ai/inference/v1/chat/completions
export LLM_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
```

### Together AI

```bash
export LLM_PROVIDER=openai_compat
export LLM_API_KEY=...
export LLM_BASE_URL=https://api.together.xyz/v1/chat/completions
export LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
```

### Local vLLM

```bash
export LLM_PROVIDER=openai_compat
export LLM_API_KEY=dummy  # vLLM doesn't require real key
export LLM_BASE_URL=http://localhost:8000/v1/chat/completions
export LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

### Ollama

```bash
export LLM_PROVIDER=openai_compat
export LLM_API_KEY=dummy  # Ollama doesn't require real key
export LLM_BASE_URL=http://localhost:11434/v1/chat/completions
export LLM_MODEL=llama3.1
```

## Provider Abstraction

The system uses a provider abstraction layer located in `backend/app/providers/`:

- `base.py` - Abstract base class and interfaces
- `openai_provider.py` - OpenAI implementation
- `openai_compatible_provider.py` - OpenAI-compatible implementation
- `factory.py` - Factory for creating providers from environment

### Usage in Code

```python
from backend.app.providers.factory import create_provider_from_env, get_model_from_env
from backend.app.providers.base import LLMRequest

# Create provider from environment
provider = create_provider_from_env()
model = get_model_from_env()

# Make a request
request = LLMRequest(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Bitcoin?"}
    ],
    model=model,
    temperature=0.7,
)

# Non-streaming
response = await provider.chat_completion(request)
print(response.text)

# Streaming
async for token in provider.stream_completion(request):
    print(token, end="", flush=True)
```

## Response Contract

All providers return responses in the same format:

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
- `message.text` MUST contain the actual assistant answer (human readable)
- `meta` MUST NOT be concatenated into `message.text`
- Frontend MUST render only `message.text`
- Frontend may show `meta` under Debug accordion if debug mode enabled

## Troubleshooting

### Meta Scaffolding Appears Instead of Answer

If you see text like "Answer: Providing a concise response based on limited details. Confidence: ...", this indicates the fallback rendering is being triggered.

**Causes:**
1. LLM provider is failing (check API key, base URL)
2. Model output is being rejected by verification
3. Timeout is too short

**Solutions:**
1. Check logs for LLM errors
2. Verify environment variables are correct
3. Increase `LLM_TIMEOUT` if needed
4. Run regression test: `pytest backend/tests/test_regression_meta_scaffolding.py`

### Provider Connection Errors

**OpenAI:**
- Verify `LLM_API_KEY` starts with `sk-`
- Check internet connectivity
- Verify no firewall blocking api.openai.com

**OpenAI-compatible:**
- Verify `LLM_BASE_URL` is correct and includes full path
- Test endpoint manually: `curl -X POST $LLM_BASE_URL -H "Authorization: Bearer $LLM_API_KEY" -H "Content-Type: application/json" -d '{"model":"...","messages":[{"role":"user","content":"test"}]}'`
- For local providers (vLLM, Ollama), ensure service is running

## Testing

Run the regression test suite:

```bash
# Test that meta scaffolding never appears
pytest backend/tests/test_regression_meta_scaffolding.py -v

# Test provider abstraction
pytest backend/tests/test_llm_providers.py -v
```

## Migration Guide

### From OpenAI to Llama (Groq)

1. Update environment variables:
   ```bash
   export LLM_PROVIDER=openai_compat
   export LLM_API_KEY=gsk_...  # Your Groq API key
   export LLM_BASE_URL=https://api.groq.com/openai/v1/chat/completions
   export LLM_MODEL=llama-3.1-70b-versatile
   ```

2. Restart the application

3. Test with a simple query: "What is Bitcoin?"

4. Verify the response is a normal explanation, not meta scaffolding

No code changes required! The abstraction layer handles all provider differences.
