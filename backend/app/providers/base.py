"""LLM Provider abstraction layer for easy switching between OpenAI and Llama-compatible providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional


@dataclass
class LLMRequest:
    """Unified request format for all LLM providers."""
    messages: list[Dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Unified response format from LLM providers."""
    text: str
    usage: Optional[Dict[str, int]] = None
    raw: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Execute a chat completion request.
        
        Args:
            request: Unified LLM request
            
        Returns:
            LLMResponse with text and metadata
            
        Raises:
            LLMProviderError: On provider-specific errors
        """
        pass
    
    @abstractmethod
    async def stream_completion(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        Execute a streaming chat completion request.
        
        Args:
            request: Unified LLM request
            
        Yields:
            Token strings as they arrive
            
        Raises:
            LLMProviderError: On provider-specific errors
        """
        pass


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    
    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


__all__ = ["LLMProvider", "LLMRequest", "LLMResponse", "LLMProviderError"]
