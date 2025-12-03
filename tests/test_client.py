"""
Unit tests for the Alpie SDK client.
"""

import pytest
import json
from unittest.mock import MagicMock
from alpie import Alpie, ChatMessage
from alpie.exceptions import (
    AuthenticationError,
    RateLimitError,
    APIError,
    ValidationError,
)


def test_client_initialization():
    """Test client initialization."""
    client = Alpie(api_key="test-key")
    assert client.api_key == "test-key"
    assert client.base_url == "https://api.169pi.com/v1"
    assert client.timeout == 60.0


def test_client_missing_api_key():
    """Test that client raises error without API key."""
    with pytest.raises(ValidationError, match="API key is required"):
        Alpie(api_key="")


def test_get_headers():
    """Test header generation."""
    client = Alpie(api_key="test-key")
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"


def test_get_headers_streaming():
    """Test header generation for streaming."""
    client = Alpie(api_key="test-key")
    headers = client._get_headers(stream=True)
    assert headers["Accept"] == "text/event-stream"


def test_non_streaming_completion(mocker):
    """Test non-streaming chat completion."""
    client = Alpie(api_key="test-key")
    
    mock_response_data = {
        "id": "chatcmpl-123",
        "model": "alpie-32b",
        "created": 1234567890,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    response = client.chat.completions.create(
        model="alpie-32b",
        messages=[ChatMessage(role="user", content="Hello")]
    )
    
    assert response.id == "chatcmpl-123"
    assert response.model == "alpie-32b"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hello! How can I help you?"
    assert response.usage.total_tokens == 30


def test_streaming_completion(mocker):
    """Test streaming chat completion."""
    client = Alpie(api_key="test-key")
    
    stream_data = [
        'data: {"id":"123","model":"alpie-32b","created":1234567890,"choices":[{"index":0,"delta":{"content":"Hello"}}]}\n\n',
        'data: {"id":"123","model":"alpie-32b","created":1234567890,"choices":[{"index":0,"delta":{"content":" there"}}]}\n\n',
        'data: [DONE]\n\n'
    ]
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_text.return_value = stream_data
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    
    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    chunks = list(client.chat.completions.create(
        model="alpie-32b",
        messages=[ChatMessage(role="user", content="Hello")],
        stream=True
    ))
    
    assert len(chunks) == 2
    assert chunks[0].delta_content == "Hello"
    assert chunks[1].delta_content == " there"


def test_api_error_401(mocker):
    """Test 401 authentication error."""
    client = Alpie(api_key="invalid-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {
            "message": "Invalid API key",
            "type": "authentication_error"
        }
    }
    
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        client.chat.completions.create(
            model="alpie-32b",
            messages=[ChatMessage(role="user", content="Hello")]
        )


def test_api_error_429(mocker):
    """Test 429 rate limit error."""
    client = Alpie(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {
        "error": {
            "message": "Rate limit exceeded",
            "type": "rate_limit_error"
        }
    }
    
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    with pytest.raises(RateLimitError, match="Rate limit exceeded"):
        client.chat.completions.create(
            model="alpie-32b",
            messages=[ChatMessage(role="user", content="Hello")]
        )


def test_streaming_error_401(mocker):
    """Test 401 authentication error in streaming mode."""
    client = Alpie(api_key="invalid-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {
            "message": "Invalid API key",
            "type": "authentication_error"
        }
    }
    mock_response.read.return_value = None
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    
    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        list(client.chat.completions.create(
            model="alpie-32b",
            messages=[ChatMessage(role="user", content="Hello")],
            stream=True
        ))


def test_streaming_error_429(mocker):
    """Test 429 rate limit error in streaming mode."""
    client = Alpie(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {
        "error": {
            "message": "Rate limit exceeded",
            "type": "rate_limit_error"
        }
    }
    mock_response.read.return_value = None
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    
    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    with pytest.raises(RateLimitError, match="Rate limit exceeded"):
        list(client.chat.completions.create(
            model="alpie-32b",
            messages=[ChatMessage(role="user", content="Hello")],
            stream=True
        ))


def test_streaming_error_500(mocker):
    """Test 500 server error in streaming mode."""
    client = Alpie(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {
        "error": {
            "message": "Internal server error",
            "type": "server_error"
        }
    }
    mock_response.read.return_value = None
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    
    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    
    mocker.patch("httpx.Client", return_value=mock_client)
    
    with pytest.raises(APIError, match="API error \\(500\\)"):
        list(client.chat.completions.create(
            model="alpie-32b",
            messages=[ChatMessage(role="user", content="Hello")],
            stream=True
        ))
