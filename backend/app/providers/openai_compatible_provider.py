"""OpenAI-compatible provider for Llama, Groq, Fireworks, Together, vLLM, etc."""

from __future__ import annotations

from .openai_provider import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """
    OpenAI-compatible provider for any service that implements the OpenAI API format.
    
    This includes:
    - Llama models via vLLM, Ollama, LM Studio
    - Groq
    - Fireworks AI
    - Together AI
    - Anyscale
    - And many others
    
    Usage:
        provider = OpenAICompatibleProvider(
            api_key="your-key",
            base_url="https://api.groq.com/openai/v1/chat/completions",
        )
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 10.0,
    ):
        """
        Initialize OpenAI-compatible provider.
        
        Args:
            api_key: API key for the service
            base_url: Full URL to the chat completions endpoint
            timeout_seconds: Request timeout
            connect_timeout_seconds: Connection timeout
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            connect_timeout_seconds=connect_timeout_seconds,
        )


__all__ = ["OpenAICompatibleProvider"]
