"""Application-specific exceptions."""


class DreamhackLocalError(Exception):
    """Base exception for the local application."""


class SessionError(DreamhackLocalError):
    """Raised when the local authenticated session is missing or invalid."""


class AccessDeniedError(DreamhackLocalError):
    """Raised when DreamHack denies access with the current session."""


class ParseError(DreamhackLocalError):
    """Raised when expected HTML structure cannot be parsed."""


class NotFoundError(DreamhackLocalError):
    """Raised when an entity cannot be found locally."""
