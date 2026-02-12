"""OpenAI provider implementation."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMRequest, LLMResponse, LLMProviderError


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 10.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.connect_timeout_seconds = connect_timeout_seconds
    
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute OpenAI chat completion."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        
        if request.extra_params:
            payload.update(request.extra_params)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        timeout = httpx.Timeout(
            self.timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "OpenAI request timeout",
                provider="openai",
                original_error=exc,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"OpenAI HTTP error: {exc}",
                provider="openai",
                original_error=exc,
            ) from exc
        except json.JSONDecodeError as exc:
            raise LLMProviderError(
                "OpenAI returned invalid JSON",
                provider="openai",
                original_error=exc,
            ) from exc
        
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            usage = data.get("usage")
            
            return LLMResponse(
                text=text,
                usage=usage,
                raw=data,
                finish_reason=finish_reason,
            )
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(
                f"OpenAI response missing expected fields: {exc}",
                provider="openai",
                original_error=exc,
            ) from exc
    
    async def stream_completion(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Execute OpenAI streaming chat completion."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        
        if request.extra_params:
            payload.update(request.extra_params)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        timeout = httpx.Timeout(
            self.timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip() or line.strip() == "data: [DONE]":
                            continue
                        
                        if line.startswith("data: "):
                            line = line[6:]
                        
                        try:
                            chunk = json.loads(line)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "OpenAI streaming timeout",
                provider="openai",
                original_error=exc,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"OpenAI streaming HTTP error: {exc}",
                provider="openai",
                original_error=exc,
            ) from exc


__all__ = ["OpenAIProvider"]
