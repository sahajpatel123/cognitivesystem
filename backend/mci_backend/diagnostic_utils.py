"""Diagnostic utilities for model output verification failures."""

import re


def sanitize_preview(text: str) -> str:
    """
    Sanitize text for safe logging preview.
    
    - Removes markdown code fences (```...```)
    - Strips leading/trailing whitespace
    - Collapses all whitespace sequences to single space
    - Truncates to 300 characters
    
    Args:
        text: Raw text to sanitize
        
    Returns:
        Sanitized preview string (max 300 chars)
    """
    if not text:
        return ""
    
    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    # Match triple backticks with optional language identifier
    sanitized = re.sub(r'```[a-z]*\n?', '', text)
    sanitized = re.sub(r'```', '', sanitized)
    
    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()
    
    # Collapse all whitespace sequences (newlines, tabs, multiple spaces) to single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Truncate to 300 characters
    if len(sanitized) > 300:
        sanitized = sanitized[:300]
    
    return sanitized


__all__ = ["sanitize_preview"]
