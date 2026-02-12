"""Utility functions for the application."""

from .request_helpers import get_request_scheme, is_https_request

__all__ = ["get_request_scheme", "is_https_request"]
