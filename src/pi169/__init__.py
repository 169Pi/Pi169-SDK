"""
Pi169 SDK
"""

from .client import Pi169Client
from .exceptions import (
    Pi169Error,
    AlpieError,
    APIError,
    AuthError,
    RateLimitError,
    TimeoutError,
    ServerError,
    EngineOverloadedError,
    ModelNotFoundError,
    LimitExceededError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    UnsupportedParamsError,
)

from .alpie_types import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    StreamChunk,
    Usage,
)

__version__ = "0.1.4"

#  Backward compatibility
Alpie = Pi169Client

__all__ = [
    # clients
    "Pi169Client",
    "AsyncPi169Client",

    # errors
    "Pi169Error",
    "AlpieError",
    "APIError",
    "AuthError",
    "RateLimitError",
    "TimeoutError",
    "ServerError",
    "EngineOverloadedError",
    "ModelNotFoundError",
    "LimitExceededError",
    "ContentPolicyViolationError",
    "ContextWindowExceededError",
    "UnsupportedParamsError",

    # types
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionChoice",
    "StreamChunk",
    "Usage",
]
