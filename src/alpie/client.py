"""
Main client class for the Alpie SDK.
"""

import json
from typing import Iterator, Optional, Union, List
import httpx

from alpie.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    TimeoutError as AlpieTimeoutError,
    ValidationError,
    NetworkError,
)
from alpie.types import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    StreamChunk,
)


class Alpie:
    """
    Main client for interacting with the Alpie API.
    
    Example:
        ```python
        from alpie import Alpie, ChatMessage
        
        client = Alpie(api_key="your-api-key")
        
        response = client.chat.completions.create(
            model="alpie-32b",
            messages=[
                ChatMessage(role="user", content="Hello!")
            ]
        )
        print(response.choices[0].message.content)
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.169pi.com/v1",
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        """
        Initialize the Alpie client.
        
        Args:
            api_key: Your Alpie API key (Bearer token)
            base_url: Base URL for the API (default: https://api.169pi.com/v1)
            timeout: Request timeout in seconds (default: 60.0)
            max_retries: Maximum number of retries for failed requests (default: 2)
        """
        if not api_key:
            raise ValidationError("API key is required")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.chat = ChatCompletions(self)
    
    def _get_headers(self, stream: bool = False) -> dict:
        """Get request headers with authentication."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if stream:
            headers["Accept"] = "text/event-stream"
        return headers
    
    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            error_data = response.json()
        except Exception:
            error_data = {"error": {"message": response.text or "Unknown error"}}
        
        error_info = error_data.get("error", {})
        if isinstance(error_info, dict):
            message = error_info.get("message", "Unknown error")
            error_type = error_info.get("type", "unknown")
        else:
            message = str(error_info)
            error_type = "unknown"
        
        status_code = response.status_code
        
        if status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {message}",
                status_code=status_code,
                response_data=error_data
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded: {message}",
                status_code=status_code,
                response_data=error_data
            )
        elif status_code >= 400:
            raise APIError(
                f"API error ({status_code}): {message}",
                status_code=status_code,
                response_data=error_data
            )


class ChatCompletions:
    """Handler for chat completion endpoints."""
    
    def __init__(self, client: Alpie):
        """Initialize with parent client."""
        self.client = client
        self.completions = self
    
    def create(
        self,
        model: str,
        messages: List[Union[ChatMessage, dict]],
        max_tokens: int = 10000,
        temperature: float = 1.0,
        stream: bool = False,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> Union[ChatCompletionResponse, Iterator[StreamChunk]]:
        """
        Create a chat completion.
        
        Args:
            model: Model to use (e.g., "alpie-32b")
            messages: List of chat messages
            max_tokens: Maximum tokens to generate (default: 10000)
            temperature: Sampling temperature (default: 1.0)
            stream: Whether to stream the response (default: False)
            top_p: Nucleus sampling parameter (default: 1.0)
            frequency_penalty: Frequency penalty (default: 0.0)
            presence_penalty: Presence penalty (default: 0.0)
        
        Returns:
            ChatCompletionResponse for non-streaming, Iterator[StreamChunk] for streaming
        
        Raises:
            ValidationError: If request validation fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            APIError: For other API errors
            NetworkError: For network-related errors
            TimeoutError: If request times out
        """
        chat_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                chat_messages.append(msg)
            elif isinstance(msg, dict):
                chat_messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
            else:
                raise ValidationError(f"Invalid message type: {type(msg)}")
        
        request = ChatCompletionRequest(
            model=model,
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
        
        if stream:
            return self._create_streaming(request)
        else:
            return self._create_non_streaming(request)
    
    def _create_non_streaming(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Create a non-streaming chat completion."""
        url = f"{self.client.base_url}/chat/completions"
        headers = self.client._get_headers(stream=False)
        payload = request.to_dict()
        
        try:
            with httpx.Client(timeout=self.client.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    self.client._handle_error_response(response)
                
                data = response.json()
                return ChatCompletionResponse.from_dict(data)
        
        except httpx.TimeoutException as e:
            raise AlpieTimeoutError(f"Request timed out: {str(e)}")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {str(e)}")
        except (AuthenticationError, RateLimitError, APIError, ValidationError):
            raise
        except Exception as e:
            raise APIError(f"Unexpected error: {str(e)}")
    
    def _create_streaming(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        """Create a streaming chat completion."""
        url = f"{self.client.base_url}/chat/completions"
        headers = self.client._get_headers(stream=True)
        payload = request.to_dict()
        
        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        response.read()
                        self.client._handle_error_response(response)
                    
                    for chunk in response.iter_text():
                        if "data: " in chunk:
                            for part in chunk.strip().split("\n\n"):
                                part = part.strip()
                                
                                if part == "data: [DONE]":
                                    return
                                
                                if not part.startswith("data: "):
                                    continue
                                
                                try:
                                    data_json = json.loads(part[6:])
                                    
                                    if "error" in data_json:
                                        error = data_json["error"]
                                        if isinstance(error, dict):
                                            message = error.get("message", "Unknown error")
                                        else:
                                            message = str(error)
                                        raise APIError(f"Streaming error: {message}", response_data=data_json)
                                    
                                    yield StreamChunk.from_dict(data_json)
                                
                                except json.JSONDecodeError:
                                    continue
        
        except httpx.TimeoutException as e:
            raise AlpieTimeoutError(f"Request timed out: {str(e)}")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {str(e)}")
        except (AuthenticationError, RateLimitError, APIError, ValidationError):
            raise
        except Exception as e:
            raise APIError(f"Unexpected streaming error: {str(e)}")
