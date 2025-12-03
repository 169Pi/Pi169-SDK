"""
Alpie SDK - Production-ready Python SDK for the Alpie reasoning model API platform.
"""

from alpie.client import Alpie
from alpie.exceptions import (
    AlpieError,
    APIError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from alpie.types import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    StreamChunk,
    Usage,
)

__version__ = "0.1.0"

__all__ = [
    "Alpie",
    "AlpieError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "TimeoutError",
    "ValidationError",
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionChoice",
    "StreamChunk",
    "Usage",
]
