"""
Alpie SDK - Production-ready Python SDK for the Alpie reasoning model API platform.
"""

from alpie.client import Alpie
from alpie.exceptions import (
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
from alpie.alpie_types import (
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
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionChoice",
    "StreamChunk",
    "Usage",
]