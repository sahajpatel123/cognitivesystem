"""Tests for diagnostic utilities."""

import pytest

from backend.mci_backend.diagnostic_utils import sanitize_preview


def test_sanitize_preview_removes_json_fences():
    """Test that JSON code fences are removed."""
    input_text = "```json\n{\"answer_text\": \"Bitcoin is a cryptocurrency\"}\n```"
    result = sanitize_preview(input_text)
    assert "```" not in result
    assert "json" not in result
    assert "answer_text" in result
    assert "Bitcoin" in result


def test_sanitize_preview_removes_plain_fences():
    """Test that plain code fences are removed."""
    input_text = "```\nSome code here\n```"
    result = sanitize_preview(input_text)
    assert "```" not in result
    assert "Some code here" in result


def test_sanitize_preview_collapses_whitespace():
    """Test that newlines and tabs are collapsed to single spaces."""
    input_text = "Line 1\n\nLine 2\t\tLine 3   Line 4"
    result = sanitize_preview(input_text)
    assert "\n" not in result
    assert "\t" not in result
    assert "  " not in result  # No double spaces
    assert result == "Line 1 Line 2 Line 3 Line 4"


def test_sanitize_preview_truncates_long_text():
    """Test that text longer than 300 chars is truncated."""
    input_text = "A" * 500
    result = sanitize_preview(input_text)
    assert len(result) == 300
    assert result == "A" * 300


def test_sanitize_preview_handles_empty_input():
    """Test that empty/None input returns empty string."""
    assert sanitize_preview("") == ""
    assert sanitize_preview(None) == ""
    assert sanitize_preview("   ") == ""


def test_sanitize_preview_strips_leading_trailing_whitespace():
    """Test that leading and trailing whitespace is removed."""
    input_text = "   \n\t  Some text here  \n\t   "
    result = sanitize_preview(input_text)
    assert result == "Some text here"


def test_sanitize_preview_complex_example():
    """Test a complex real-world example."""
    input_text = """```json
{
    "answer_text": "Bitcoin is a decentralized digital currency.",
    "assumptions": ["User knows basic finance"]
}
```"""
    result = sanitize_preview(input_text)
    assert "```" not in result
    assert "\n" not in result
    assert "answer_text" in result
    assert "Bitcoin" in result
    # Should be collapsed to single-line with spaces
    assert len(result) < len(input_text)


def test_sanitize_preview_preserves_content_order():
    """Test that content order is preserved after sanitization."""
    input_text = "First\nSecond\nThird"
    result = sanitize_preview(input_text)
    assert result == "First Second Third"
    assert result.index("First") < result.index("Second") < result.index("Third")
