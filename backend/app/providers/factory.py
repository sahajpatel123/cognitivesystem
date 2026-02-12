"""LLM Provider factory for creating providers from environment configuration."""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .openai_compatible_provider import OpenAICompatibleProvider


def create_provider_from_env() -> LLMProvider:
    """
    Create an LLM provider from environment variables.
    
    Environment variables:
        LLM_PROVIDER: "openai" or "openai_compat" (default: "openai")
        LLM_API_KEY: API key for the provider (required)
        LLM_BASE_URL: Base URL for the provider (optional for OpenAI, required for openai_compat)
        LLM_MODEL: Model name (optional, used by caller)
        LLM_TIMEOUT: Request timeout in seconds (default: 30.0)
        LLM_CONNECT_TIMEOUT: Connection timeout in seconds (default: 10.0)
    
    Returns:
        Configured LLM provider instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    provider_type = os.getenv("LLM_PROVIDER", "openai").lower()
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    timeout = float(os.getenv("LLM_TIMEOUT", "30.0"))
    connect_timeout = float(os.getenv("LLM_CONNECT_TIMEOUT", "10.0"))
    
    if not api_key:
        raise ValueError("LLM_API_KEY environment variable is required")
    
    if provider_type == "openai":
        # OpenAI provider - base_url is optional
        if base_url:
            return OpenAIProvider(
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout,
                connect_timeout_seconds=connect_timeout,
            )
        else:
            return OpenAIProvider(
                api_key=api_key,
                timeout_seconds=timeout,
                connect_timeout_seconds=connect_timeout,
            )
    
    elif provider_type == "openai_compat":
        # OpenAI-compatible provider - base_url is required
        if not base_url:
            raise ValueError("LLM_BASE_URL is required for openai_compat provider")
        
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout,
            connect_timeout_seconds=connect_timeout,
        )
    
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider_type}. Must be 'openai' or 'openai_compat'")


def get_model_from_env() -> str:
    """
    Get the model name from environment variables.
    
    Returns:
        Model name (default: "gpt-4")
    """
    return os.getenv("LLM_MODEL", "gpt-4")


__all__ = ["create_provider_from_env", "get_model_from_env"]
