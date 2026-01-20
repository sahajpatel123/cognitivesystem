class ProviderDisabledError(Exception):
    """Raised when model calls are disabled via kill switch."""


class ProviderMisconfiguredError(Exception):
    """Raised when provider configuration is missing or invalid."""


class ProviderTimeoutError(Exception):
    """Raised when provider call times out."""


class ProviderCircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__("circuit open")
        self.retry_after = retry_after


class ProviderUpstreamError(Exception):
    """Raised for upstream provider failures."""


__all__ = [
    "ProviderDisabledError",
    "ProviderMisconfiguredError",
    "ProviderTimeoutError",
    "ProviderCircuitOpenError",
    "ProviderUpstreamError",
]
