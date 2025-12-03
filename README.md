# Alpie SDK

Production-ready Python SDK for the Alpie reasoning model API platform. Simplifies integration for developers with comprehensive error handling, streaming support, and a clean Python interface.

## Features

- ✅ **Streaming & Non-Streaming Support** - Handle both direct and streaming chat completions
- ✅ **Robust Error Handling** - Comprehensive error handling for API errors, rate limiting, network issues, and timeouts
- ✅ **Clean Python Interface** - Type hints, dataclasses, and intuitive API design
- ✅ **Production Ready** - Proper authentication management, retry logic, and timeout handling
- ✅ **Well Tested** - Comprehensive unit tests with pytest
- ✅ **Type Safe** - Full type hints for better IDE support and code quality

## Installation

```bash
pip install alpie-sdk
```

For development:
```bash
pip install alpie-sdk[dev]
```

## Quick Start

### Basic Usage (Non-Streaming)

```python
from alpie import Alpie, ChatMessage

client = Alpie(api_key="your-api-key-here")

response = client.chat.completions.create(
    model="alpie-32b",
    messages=[
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="What is Python?")
    ],
    max_tokens=1000
)

print(response.choices[0].message.content)
```

### Streaming Usage

```python
from alpie import Alpie, ChatMessage

client = Alpie(api_key="your-api-key-here")

stream = client.chat.completions.create(
    model="alpie-32b",
    messages=[
        ChatMessage(role="user", content="Write a poem about coding")
    ],
    stream=True
)

for chunk in stream:
    if chunk.delta_content:
        print(chunk.delta_content, end="", flush=True)
```

### Using Dictionary Format

```python
response = client.chat.completions.create(
    model="alpie-32b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)
```

## API Reference

### Client Initialization

```python
Alpie(
    api_key: str,                                # Required: Your Alpie API key
    base_url: str = "https://api.169pi.com/v1", # Optional: API base URL
    timeout: float = 60.0,                       # Optional: Request timeout in seconds
    max_retries: int = 2,                        # Optional: Max retries for failed requests
)
```

### Chat Completions

```python
client.chat.completions.create(
    model: str,                          # Required: Model name (e.g., "alpie-32b")
    messages: List[ChatMessage | dict],  # Required: List of messages
    max_tokens: int = 10000,             # Optional: Maximum tokens to generate
    temperature: float = 1.0,            # Optional: Sampling temperature (0.0-2.0)
    stream: bool = False,                # Optional: Enable streaming
    top_p: float = 1.0,                  # Optional: Nucleus sampling parameter
    frequency_penalty: float = 0.0,      # Optional: Frequency penalty (-2.0 to 2.0)
    presence_penalty: float = 0.0,       # Optional: Presence penalty (-2.0 to 2.0)
)
```

## Error Handling

The SDK provides specific exception types for different error scenarios:

```python
from alpie import Alpie
from alpie.exceptions import (
    AuthenticationError,
    RateLimitError,
    APIError,
    TimeoutError,
    NetworkError,
    ValidationError
)

client = Alpie(api_key="your-api-key")

try:
    response = client.chat.completions.create(
        model="alpie-32b",
        messages=[{"role": "user", "content": "Hello"}]
    )
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e.message}")
except APIError as e:
    print(f"API error: {e.message} (status: {e.status_code})")
except TimeoutError as e:
    print(f"Request timed out: {e.message}")
except NetworkError as e:
    print(f"Network error: {e.message}")
```

## Response Objects

### ChatCompletionResponse (Non-Streaming)

```python
response = client.chat.completions.create(...)

response.id                    # Completion ID
response.model                 # Model used
response.created               # Timestamp
response.choices[0].message.content    # Response content
response.choices[0].finish_reason      # Why completion finished
response.usage.prompt_tokens   # Tokens in prompt
response.usage.completion_tokens   # Tokens in completion
response.usage.total_tokens    # Total tokens used
```

### StreamChunk (Streaming)

```python
for chunk in client.chat.completions.create(..., stream=True):
    chunk.id                   # Chunk ID
    chunk.model                # Model used
    chunk.delta_content        # Content delta
    chunk.finish_reason        # Finish reason (if last chunk)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Building the Package

```bash
python -m build
```

## Examples

See the `examples/` directory for more examples:

- `examples/simple_chat.py` - Basic non-streaming chat
- `examples/streaming_chat.py` - Streaming responses
- `examples/chat_cli.py` - Interactive command-line chat interface

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/alpie-sdk/issues
- Documentation: https://github.com/yourusername/alpie-sdk#readme

## Changelog

### v0.1.0 (2024-11-24)
- Initial release
- Non-streaming chat completions
- Streaming chat completions
- Comprehensive error handling
- Type hints and documentation
- Unit tests
