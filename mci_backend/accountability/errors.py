class AccountabilityError(RuntimeError):
    """Base class for accountability scaffolding errors."""


class InvalidTraceError(AccountabilityError):
    """Raised when a decision trace is missing required structure or markers."""


class EvidenceMissingError(AccountabilityError):
    """Raised when required rule or boundary evidence is absent."""


class AttributionMissingError(AccountabilityError):
    """Raised when attribution is requested without sufficient evidence."""


class AuditNotReadyError(AccountabilityError):
    """Raised when an audit replay bundle is incomplete or inconsistent."""
