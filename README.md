# Pi169 Python SDK

The Pi169 SDK provides a clean, type-safe, and robust interface for interacting with the Alpie 32B reasoning model.
Designed for production workloads with **streaming support, async/await patterns, CLI integration, retries, timeouts, typed exceptions, and intuitive APIs**.

## Installation
```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pi169
```

Python 3.10+ required

## Authentication

Pi169 uses Bearer Token authentication.

**Synchronous Client:**
```python
from pi169 import Pi169Client

client = Pi169Client(api_key="YOUR_API_KEY")
```

**Asynchronous Client:**
```python
from pi169.async_client import AsyncPi169Client

client = AsyncPi169Client(api_key="YOUR_API_KEY")
```

Every request automatically sends ([Create API Key](https://playground.169pi.ai/dashboard/api-keys)):
```
Authorization: Bearer <API_KEY>
```

## Base URL & Client Configuration

**Synchronous Client:**
```python
from pi169 import Pi169Client

client = Pi169Client(
    api_key="YOUR_API_KEY",
    base_url="https://api.169pi.com/v1",
    timeout=60.0,
    max_retries=2,
)
```

**Asynchronous Client:**
```python
from pi169.async_client import AsyncPi169Client

client = AsyncPi169Client(
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

- **CLI Integration** for quick command-line interactions
- Streaming & Non-Streaming Chat Completions
- **Async/Await Support** for high-performance concurrent requests
- Clean, type-safe Python Interface (dataclasses, type hints)
- Robust Error Handling with typed exceptions
- Production-Ready Networking (retries, timeouts, httpx)
- Fully Tested with pytest
- Optimized for Reasoning Models

## CLI Integration

The Pi169 SDK includes a powerful command-line interface for quick interactions with the Alpie model directly from your terminal.

### Setting Up Your API Key

Before using the CLI, set your API key as an environment variable:

**macOS/Linux:**
```bash
export ALPIE_API_KEY="your_api_key_here"
```

**Windows Command Prompt:**
```cmd
set ALPIE_API_KEY=your_api_key_here
```

**Windows PowerShell:**
```powershell
$env:ALPIE_API_KEY = "your_api_key_here"
```

### CLI Usage

**Non-Streaming Mode (default):**
```bash
pi169 "What is the capital of France?"
```

**Streaming Mode:**
```bash
pi169 "What is the capital of France?" --stream
```

The CLI automatically uses the `ALPIE_API_KEY` environment variable for authentication, making it easy to interact with the API without writing any code.

### CLI Options

- `--stream` → Enable streaming mode for real-time token-by-token responses

### Synchronous Usage

#### Non-Streaming Chat Completion
```python
import os
from dotenv import load_dotenv
from pi169 import Pi169Client

load_dotenv()

api_key = os.getenv("ALPIE_API_KEY")
if not api_key:
    raise ValueError("API key missing")

client = Pi169Client(api_key=api_key)

response = client.chat.completions.create(
    model="alpie-32b",
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ],
    stream=False,
)

# Print the assistant reply
if response.choices:
    message = response.choices[0].message
    if message and message.content:
        print(message.content)
else:
    print("No choices returned")
```

#### Streaming Chat Completion
```python
import os
from dotenv import load_dotenv
from pi169 import Pi169Client

load_dotenv()

api_key = os.getenv("ALPIE_API_KEY")
if not api_key:
    raise ValueError("API key missing")

client = Pi169Client(api_key=api_key)

stream = client.chat.completions.create(
    model="alpie-32b",
    messages=[{"role": "user", "content": "what is the capital of france?"}],
    stream=True,
)

for chunk in stream:
    if not chunk.choices:
        continue

    choice = chunk.choices[0]   
    delta = choice.get("delta", {})

    content = delta.get("content")
    if content:
        print(content, end="", flush=True)
```

Streaming responses yield partial tokens in real time — ideal for chatbots, UIs, and live applications.

---

### Asynchronous Usage

#### Non-Streaming Chat Completion (Async)
```python
import asyncio
import os
from dotenv import load_dotenv
from pi169.async_client import AsyncPi169Client

load_dotenv()

async def main():
    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        raise ValueError("API key missing")

    client = AsyncPi169Client(api_key=api_key)

    response = await client.chat.completions.create(
        model="alpie-32b",
        messages=[
            {"role": "user", "content": "What is the capital of France?"}
        ],
    )

    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
```

#### Streaming Chat Completion (Async)
```python
import asyncio
import os
from dotenv import load_dotenv
from pi169.async_client import AsyncPi169Client

load_dotenv()

async def main():
    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        raise ValueError("API key missing")

    client = AsyncPi169Client(api_key=api_key)

    stream = await client.chat.completions.create(
        model="alpie-32b",
        messages=[
            {"role": "user", "content": "What is the capital of France?"}
        ],
        stream=True,
    )

    async for chunk in stream:
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        delta = choice.get("delta", {})

        content = delta.get("content")
        if content:
            print(content, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
```

#### Concurrent Requests (Async)
Process multiple requests concurrently for better performance:

```python
import asyncio
import os
from dotenv import load_dotenv
from pi169.async_client import AsyncPi169Client

load_dotenv()

async def main():
    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        raise ValueError("API key missing")

    client = AsyncPi169Client(api_key=api_key)

    # Create multiple tasks
    tasks = [
        client.chat.completions.create(
            model="alpie-32b",
            messages=[{"role": "user", "content": f"What is {n} + {n}?"}]
        )
        for n in range(1, 6)
    ]

    # Execute concurrently
    responses = await asyncio.gather(*tasks)

    for i, response in enumerate(responses, 1):
        print(f"Response {i}: {response.choices[0].message.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Available Models

| Model | Parameters | Description |
|-------|------------|-------------|
| alpie-32b | 32B | Advanced reasoning model |

### Performance Benchmarks

![Alpie 32B Benchmark Results](Benchmark.png)

## Rate Limits and Quotas

Pi169 enforces rate limits to ensure fair and stable usage of the API.

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
- **Use async client for concurrent requests** to maximize throughput while respecting rate limits

## Error Handling

The SDK includes a full typed exception hierarchy for safe and predictable error handling.

### Base Exception
```python
class Pi169Error(Exception):
    ...
```

### Exception Hierarchy
```
Pi169Error
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

### Catching Errors (Sync)

**Catch all Pi169-related errors:**
```python
from pi169 import Pi169Error

try:
    client.chat.completions.create(...)
except Pi169Error as e:
    print("Error:", e.message)
```

**Catch specific errors:**
```python
from pi169 import (
    Pi169Client,
    AuthError,
    RateLimitError,
    TimeoutError,
    KeyNotActive,
    ModelNotFoundError,
    Pi169Error,
)

client = Pi169Client(api_key="YOUR_API_KEY")

try:
    response = client.chat.completions.create(
        model="alpie-32b",
        messages=[{"role": "user", "content": "Hello!"}],
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

except Pi169Error as e:
    print("A Pi169 SDK error occurred:", e)

else:
    print("Response:", response.choices[0].message.content)
```

### Catching Errors (Async)

Error handling works identically in async contexts:

```python
import asyncio
from pi169.async_client import AsyncPi169Client
from pi169 import (
    AuthError,
    RateLimitError,
    TimeoutError,
    KeyNotActive,
    ModelNotFoundError,
    Pi169Error,
)

async def main():
    client = AsyncPi169Client(api_key="YOUR_API_KEY")

    try:
        response = await client.chat.completions.create(
            model="alpie-32b",
            messages=[{"role": "user", "content": "Hello!"}],
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

    except Pi169Error as e:
        print("A Pi169 SDK error occurred:", e)

    else:
        print("Response:", response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
```

### Error-to-Exception Mapping

| API Error | SDK Exception |
|-----------|---------------|
| 401 auth failure | AuthError |
| 402 key not active | KeyNotActive |
| 400 invalid params | UnsupportedParamsError |
| 413 context window exceeded | ContextWindowExceededError |
| 404 model not found | ModelNotFoundError |
| 429 rate limit exceeded | RateLimitError |
| 500 internal server error | ServerError |
| 503 engine overloaded | EngineOverloadedError |

## Best Practices

### When to Use CLI vs Python SDK

**Use CLI when:**
- Quick testing or prototyping
- One-off queries or experiments
- Shell scripting and automation
- Learning the API without writing code
- Debugging API responses

**Use Python SDK when:**
- Building applications or services
- Need complex conversation flows
- Require error handling and retries
- Processing multiple requests
- Integration with existing Python code

### When to Use Async vs Sync

**Use Async when:**
- Making multiple concurrent API requests
- Building high-performance web servers (FastAPI, aiohttp)
- Integrating with other async libraries
- Handling many simultaneous streaming connections
- You need maximum throughput within rate limits

**Use Sync when:**
- Writing simple scripts
- Making sequential requests
- Working in environments without async support
- Prototyping or learning

## Recommended Project Structure
```
pi169/
├── __init__.py
├── client.py
├── async_client.py
├── cli.py
├── chat/
│   ├── completions.py
│   └── async_completions.py
├── types.py
├── errors.py
└── utils/
    └── http.py
```

## Testing

The Pi169 SDK includes a complete pytest-based test suite.

**Run all tests:**
```bash
pytest
```

### Test Directory Structure
```
project-root/
│
├── src/
│   └── pi169/
│       ├── __init__.py
│       ├── client.py
│       ├── async_client.py
│       ├── cli.py
│       ├── errors.py
│       ├── types.py
│       ├── chat/
│       │   ├── completions.py
│       │   ├── async_completions.py
│       │   └── schemas.py
│       └── utils/
│           └── http.py
│
└── tests/
    ├── test_streaming.py
    ├── test_async_streaming.py
    ├── test_error_mapping.py
    ├── test_async_error_mapping.py
    ├── test_timeout.py
    ├── test_async_timeout.py
    ├── test_retry_logic.py
    ├── test_async_retry_logic.py
    ├── test_chat_completions.py
    ├── test_async_chat_completions.py
    └── test_cli.py
```

### What Each Test File Covers

| Test File | Purpose |
|-----------|---------|
| test_streaming.py | Verifies streaming responses & chunk iteration |
| test_async_streaming.py | Verifies async streaming responses |
| test_error_mapping.py | Ensures correct mapping to SDK exceptions |
| test_async_error_mapping.py | Tests async error handling |
| test_timeout.py | Tests request timeout behavior |
| test_async_timeout.py | Tests async timeout behavior |
| test_retry_logic.py | Validates retry handling on failures |
| test_async_retry_logic.py | Tests async retry logic |
| test_chat_completions.py | Tests non-streaming chat completion flow |
| test_async_chat_completions.py | Tests async non-streaming completions |
| test_cli.py | Tests CLI functionality and argument parsing |

### Install Test Dependencies
```bash
pip install pytest pytest-httpx pytest-asyncio respx pytest-mock
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

**Run async tests:**
```bash
pytest tests/test_async_streaming.py
```

**Run CLI tests:**
```bash
pytest tests/test_cli.py
```

**Run a single test:**
```bash
pytest tests/test_streaming.py::test_basic_stream
```

## Environment Variables

The SDK works seamlessly with environment variables for secure API key management:

```bash
# .env file
ALPIE_API_KEY=your_api_key_here
```

```python
import os
from dotenv import load_dotenv
from pi169 import Pi169Client

load_dotenv()

api_key = os.getenv("ALPIE_API_KEY")
client = Pi169Client(api_key=api_key)
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
- Whether you're using sync, async, or CLI

## Changelog

### Version 0.1.0

**New Features:**
- Added CLI integration for command-line interactions
- Added async/await support with `AsyncPi169Client` client
- Added async streaming support
- Added async error handling
- Added concurrent request examples
- Added context manager support for both sync and async clients
- Added chat completions (sync and streaming)
- Added typed exceptions and error mapping
- Added retry logic, timeout configuration, and base client setup
- Added available models listing
- Added full pytest-based test suite

**Documentation:**
- Added CLI usage guide and examples
- Added comprehensive async usage examples
- Added best practices for CLI vs Python SDK and sync vs async
- Updated test suite documentation
- Added environment variable support examples

## License

Apache 2.0

© 169PI
