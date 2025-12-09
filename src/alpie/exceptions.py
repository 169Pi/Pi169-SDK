"""
Exception classes for the Alpie SDK.
"""

from typing import Optional, Dict, Any


class AlpieError(Exception):
    """Base exception for all Alpie SDK errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self):
        # Prefer backend message if provided
        base = self.message

        if self.status_code:
            base = f"[{self.status_code}] {base}"

        # Show backend-provided JSON error message if available
        if self.response_data and "error" in self.response_data:
            err = self.response_data["error"]
            msg = err.get("message")
            if msg and msg != self.message:
                base += f" | Details: {msg}"

        return base


class APIError(AlpieError):
    """Raised when the API returns an error response."""
    pass


class ContentPolicyViolationError(AlpieError):
    """Raised when authentication fails (401)."""
    pass
class ContextWindowExceededError(AlpieError):
    """Raised when the context window is exceeded."""
    pass



class UnsupportedParamsError(AlpieError):
    """Raised when a request times out."""
    pass


class AuthError(AlpieError):
    """Raised when request validation fails."""
    pass


class RateLimitError(AlpieError):
    """Raised when a network error occurs."""
    pass

class ServerError(AlpieError):
    """Raised when the specified model is not found."""
    pass

class EngineOverloadedError(AlpieError):
    """Raised when usage limit is exceeded."""
    pass

class TimeoutError(AlpieError):
    """Raised when the specified model is not found."""
    pass

class ModelNotFoundError(AlpieError):
    """Raised when usage limit is exceeded."""
    pass

class LimitExceededError(AlpieError):
    """Raised when usage limit is exceeded."""
    pass    
class  KeyNotActive(AlpieError):
    pass
