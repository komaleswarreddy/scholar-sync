"""
Custom Exceptions

Custom exception classes for the application.
"""


class ScholarSyncException(Exception):
    """Base exception for ScholarSync."""
    pass


class ValidationError(ScholarSyncException):
    """Validation error."""
    pass


class NotFoundError(ScholarSyncException):
    """Resource not found error."""
    pass


class AuthenticationError(ScholarSyncException):
    """Authentication error."""
    pass


class AuthorizationError(ScholarSyncException):
    """Authorization error."""
    pass

