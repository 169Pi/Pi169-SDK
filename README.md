# Alpie Python SDK

The Alpie SDK provides a clean, type-safe, and robust interface for interacting with the Alpie 32B reasoning model.
Designed for production workloads with streaming support, retries, timeouts, typed exceptions, and intuitive APIs.

## Installation
```bash
pip install alpie-chat-sdk
```

Python 3.10+ required

## Authentication

Alpie uses Bearer Token authentication.
```python
from alpie import Alpie

client = Alpie(api_key="YOUR_API_KEY")
```

Every request automatically sends ([Create API Key](https://api.169pi.com)):
```
Authorization: Bearer <API_KEY>
```

## Base URL & Client Configuration
```python
client = Alpie(
    api_key="YOUR_API_KEY",
    base_url="https://api.169pi.com/v1",
    timeout=60.0,
    max_retries=2,
)
```

- `base_url` → API root
- `timeout` → max wait time
- `max_retries` → safe retry logic for network issues

## Features

- Streaming & Non-Streaming Chat Completions
- Clean, type-safe Python Interface (dataclasses, type hints)
- Robust Error Handling with typed exceptions
- Production-Ready Networking (retries, timeouts, httpx)
- Fully Tested with pytest
- Optimized for Reasoning Models

## Quickstart Examples

### Non-Streaming Chat Completion
```python
from alpie import Alpie, ChatMessage

client = Alpie(api_key="YOUR_API_KEY")

response = client.chat.completions.create(
    model="alpie-22b",
    messages=[
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="What is Python?")
    ],
    max_tokens=10000,
)

print(response.choices[0].message.content)
```

### Streaming Chat Completion
```python
from alpie import Alpie, ChatMessage

client = Alpie(api_key="YOUR_API_KEY")

stream = client.chat.completions.create(
    model="alpie-32b",
    messages=[
        ChatMessage(role="user", content="tell me a poem about coding")
    ],
    stream=True,
    max_tokens=5000,
)

for chunk in stream:
    if chunk.delta_content:
        print(chunk.delta_content, end="", flush=True)
```

Streaming responses yield partial tokens in real time — ideal for chatbots, UIs, and live applications.

## Available Models

| Model | Parameters | Description |
|-------|------------|-------------|
| alpie-32b | 32B | Advanced reasoning model |

## Rate Limits and Quotas

Alpie enforces rate limits to ensure fair and stable usage of the API.

### General Rate Limits

- **Requests per minute (RPM):** 60
- **Requests per hour (RPH):** 1000

If you exceed the limit, the API will return:
```json
{
  "status": 429,
  "error": "rate_limit_exceeded"
}
```

### Retry and Backoff Recommendations

- Wait for the `Retry-After` header
- Avoid retry storms by ensuring you do not send parallel retries

### Best Practices

- Batch multiple operations into fewer requests
- Use streaming for long outputs to avoid token bursts
- Maintain conversation history efficiently
- Cache responses when appropriate
- Spread requests evenly instead of sending them in spikes

## Error Handling

The SDK includes a full typed exception hierarchy for safe and predictable error handling.

### Base Exception
```python
class AlpieError(Exception):
    ...
```

### Exception Hierarchy
```
AlpieError
├── APIError
├── ContentPolicyViolationError
├── ContextWindowExceededError
├── UnsupportedParamsError
├── AuthError
├── RateLimitError
├── ServerError
├── EngineOverloadedError
├── TimeoutError
├── ModelNotFoundError
├── LimitExceededError
└── KeyNotActive
```

### Example Error Response (from backend)
```json
{
  "error": {
    "message": "Key not active",
    "type": "key_not_active",
    "code": 402
  }
}
```

SDK automatically maps this to:
```python
KeyNotActive("Key not active", status_code=402, response_data={...})
```

### Catching Errors

**Catch all Alpie-related errors:**
```python
from alpie import AlpieError

try:
    client.chat.completions.create(...)
except AlpieError as e:
    print("Error:", e.message)
```

**Catch specific errors:**
```python
from alpie import (
    Alpie,
    AuthError,
    RateLimitError,
    TimeoutError,
    ModelNotFoundError,
    AlpieError,
    ChatMessage,
)

client = Alpie(api_key="YOUR_API_KEY")

try:
    response = client.chat.completions.create(
        model="alpie-32b",
        messages=[ChatMessage(role="user", content="Hello!")],
        max_tokens=100
    )

except AuthError:
    print("Invalid API key.")

except KeyNotActive:
    print("Your API key is not active.")

except RateLimitError:
    print("Rate limit exceeded. Please try again later.")

except TimeoutError:
    print("The request timed out.")

except ModelNotFoundError:
    print("The requested model does not exist.")

except AlpieError as e:
    print("An Alpie SDK error occurred:", e)

else:
    print("Response:", response.choices[0].message.content)
```

### Error-to-Exception Mapping

| API Error | SDK Exception |
|-----------|---------------|
| 401 auth failure | AuthError |
| 400 invalid params | UnsupportedParamsError |
| 413 context window exceeded | ContextWindowExceededError |
| 404 model not found | ModelNotFoundError |
| 429 rate limit exceeded | RateLimitError |
| 500 internal server error | ServerError |
| 503 engine overloaded | EngineOverloadedError |

## Recommended Project Structure
```
alpie/
├── __init__.py
├── client.py
├── chat/
│   ├── completions.py
├── types.py
├── errors.py
├── utils/
│   └── http.py
```

## Testing

The Alpie SDK includes a complete pytest-based test suite.

**Run all tests:**
```bash
pytest
```

### Test Directory Structure
```
project-root/
│
├── alpie/
│   ├── __init__.py
│   ├── client.py
│   ├── errors.py
│   ├── types.py
│   ├── chat/
│   │   ├── completions.py
│   │   └── schemas.py
│   └── utils/
│       └── http.py
│
└── tests/
    ├── test_streaming.py
    ├── test_error_mapping.py
    ├── test_timeout.py
    ├── test_retry_logic.py
    └── test_chat_completions.py
```

### What Each Test File Covers

| Test File | Purpose |
|-----------|---------|
| test_streaming.py | Verifies streaming responses & chunk iteration |
| test_error_mapping.py | Ensures correct mapping to SDK exceptions |
| test_timeout.py | Tests request timeout behavior |
| test_retry_logic.py | Validates retry handling on failures |
| test_chat_completions.py | Tests non-streaming chat completion flow |

### Install Test Dependencies
```bash
pip install pytest pytest-httpx respx
```

This allows mocking API responses so tests run offline.

### Running the Tests

**Run all tests:**
```bash
pytest
```

**Verbose mode:**
```bash
pytest -v
```

**Run a single test file:**
```bash
pytest tests/test_streaming.py
```

**Run a single test:**
```bash
pytest tests/test_streaming.py::test_basic_stream
```

## Support

For questions, feature requests, or bug reports:

- **GitHub Issues:** [https://github.com/169pi/Alpie-Chat-SDK/issues](https://github.com/169pi/Alpie-Chat-SDK/issues)
- **Support Email:** contact@169pi.com

When contacting support, include:

- SDK version
- Python version
- API endpoint used
- Error message or traceback
- Minimal reproducible example if possible

## Changelog

### Version 0.1.0

Initial release of the Alpie Python SDK
- Added chat completions (sync and streaming)
- Added typed exceptions and error mapping
- Added retry logic, timeout configuration, and base client setup
- Added available models listing
- Added full pytest-based test suite

Future versions will document
- Bug fixes
- Added features
- Deprecations

## License

Apache 2.0

© 169PI
