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


class APIError(AlpieError):
    """Raised when the API returns an error response."""
    pass


class AuthenticationError(AlpieError):
    """Raised when authentication fails (401)."""
    pass


class RateLimitError(AlpieError):
    """Raised when rate limit is exceeded (429)."""
    pass


class TimeoutError(AlpieError):
    """Raised when a request times out."""
    pass


class ValidationError(AlpieError):
    """Raised when request validation fails."""
    pass


class NetworkError(AlpieError):
    """Raised when a network error occurs."""
    pass
