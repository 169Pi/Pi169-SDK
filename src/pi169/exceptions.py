"""
Exception classes for the Pi169 SDK.
"""

from typing import Optional, Dict, Any


class Pi169Error(Exception):
    """Base exception for all Pi169 SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


# 🔁 Backward compatibility
class AlpieError(Pi169Error):
    """Deprecated: use Pi169Error instead."""
    pass


class APIError(Pi169Error):
    pass


class ContentPolicyViolationError(Pi169Error):
    pass


class ContextWindowExceededError(Pi169Error):
    pass


class UnsupportedParamsError(Pi169Error):
    pass


class AuthError(Pi169Error):
    pass


class RateLimitError(Pi169Error):
    pass


class ServerError(Pi169Error):
    pass


class EngineOverloadedError(Pi169Error):
    pass


class TimeoutError(Pi169Error):
    pass


class ModelNotFoundError(Pi169Error):
    pass


class LimitExceededError(Pi169Error):
    pass


class KeyNotActive(Pi169Error):
    pass
