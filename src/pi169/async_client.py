import json
from typing import AsyncIterator, Optional, Union, List
import httpx

from pi169.exceptions import (
    APIError,
    AuthError,
    RateLimitError,
    TimeoutError as ApiTimeoutError,
    ServerError,
    EngineOverloadedError,
    ModelNotFoundError,
    LimitExceededError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    UnsupportedParamsError,
    KeyNotActive
)

from pi169.alpie_types import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    StreamChunk,
)


class AsyncPi169Client:
    """
    Asynchronous client for interacting with the 169Pi API.

    This client handles authentication, request formulation, and error handling
    for async chat completions. It is designed to be used within an `asyncio` 
    event loop.

    Args:
        api_key (str): Your 169Pi API key for authentication.
        base_url (str, optional): The base URL for the API. 
            Defaults to "https://api.169pi.com/v1".
        timeout (float, optional): Request timeout in seconds. Defaults to 60.0.
        max_retries (int, optional): Number of times to retry failed requests. 
            Defaults to 2.

    Attributes:
        chat (AsyncChatCompletions): Access to chat completion endpoints.

    Basic usage inside an async function:

    >>> import asyncio
    >>> from pi169.async_client import AsyncPi169Client
    >>>
    >>> async def main():
    >>>     client = AsyncPi169Client(api_key="your_api_key")
    >>>
    >>>     # Non-streaming request
    >>>     response = await client.chat.completions.create(
    >>>         model="alpie-32b",
    >>>         messages=[{"role": "user", "content": "Hello!"}]
    >>>     )
    >>>     print(response.choices[0].message.content)
    >>>
    >>> asyncio.run(main())

    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.169pi.com/v1",  # Updated URL placeholder based on context
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        if not api_key:
            raise AuthError("API key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.chat = AsyncChatCompletions(self)

    def _get_headers(self, stream: bool = False) -> dict:
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
            message = (
                error_info.get("message") or
                error_data.get("detail") or
                error_data.get("error_description") or
                str(error_info) or
                response.text or
                "Unknown error"
            )
            error_type = error_info.get("type", "unknown")
        else:
            message = (
                str(error_info) or
                error_data.get("message") or
                error_data.get("detail") or
                response.text or
                "Unknown error"
            )
            error_type = "unknown"

        status_code = response.status_code

        if status_code == 401:
            if message.lower() in ["error", "unauthorized", ""]:
                message = "Invalid API key. Please check your API key and try again."
            raise AuthError(message, status_code, error_data)

        if status_code == 400:
            if error_type == "content_policy_violation":
                raise ContentPolicyViolationError(message, status_code, error_data)
            elif error_type == "context_window_exceeded":
                raise ContextWindowExceededError(message, status_code, error_data)
            elif error_type == "unsupported_params":
                raise UnsupportedParamsError(message, status_code, error_data)
            else:
                raise APIError(message, status_code, error_data)

        if status_code == 402:
            if error_type == "limit_exceeded":
                raise LimitExceededError(message, status_code, error_data)
            elif error_type == "key_not_active":
                raise KeyNotActive(message, status_code, error_data)
            else:
                raise APIError(message, status_code, error_data)

        if status_code == 403:
            raise ContentPolicyViolationError(message, status_code, error_data)

        if status_code == 404:
            raise ModelNotFoundError(message, status_code, error_data)

        if status_code == 429:
            raise RateLimitError(message, status_code, error_data)

        if status_code == 503:
            raise EngineOverloadedError(message, status_code, error_data)

        if status_code == 504:
            raise ApiTimeoutError(message, status_code, error_data)

        if 500 <= status_code <= 599:
            raise ServerError(f"Server error {status_code}: {message}", status_code, error_data)

        raise APIError(f"API error {status_code}: {message}", status_code, error_data)


class AsyncChatCompletions:
    """
    Async handler for chat completion endpoints.

    This class provides methods to generate model responses asynchronously.
    It supports both standard request-response patterns and streaming responses
    via Server-Sent Events (SSE).
    """

    def __init__(self, client: AsyncPi169Client):
        self.client = client
        self.completions = self

    async def create(
        self,
        model: str,
        messages: List[Union[ChatMessage, dict]],
        max_tokens: int = 10000,
        temperature: float = 1.0,
        stream: bool = False,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> Union[ChatCompletionResponse, AsyncIterator[StreamChunk]]:
        """
        Asynchronously creates a model response for the given chat conversation.

        Args:
            model (str): The name of the model to use (e.g., "alpie-32b").
            messages (List[Union[ChatMessage, dict]]): A list of messages comprising 
                the conversation so far. Each message should be a dictionary or 
                ChatMessage object with 'role' and 'content' keys.
            max_tokens (int, optional): The maximum number of tokens to generate 
                in the completion. Defaults to 10000.
            temperature (float, optional): Sampling temperature to use, between 0.0 and 1.0. 
                Higher values make output more random, lower values more deterministic. 
                Defaults to 1.0.
            stream (bool, optional): If True, partial message deltas will be sent 
                as data-only server-sent events as they become available. 
                Defaults to False.
            top_p (float, optional): An alternative to sampling with temperature, 
                called nucleus sampling. Defaults to 1.0.
            frequency_penalty (float, optional): Number between -2.0 and 2.0. 
                Positive values penalize new tokens based on their existing frequency 
                in the text so far. Defaults to 0.0.
            presence_penalty (float, optional): Number between -2.0 and 2.0. 
                Positive values penalize new tokens based on whether they appear 
                in the text so far. Defaults to 0.0.

        Returns:
            Union[ChatCompletionResponse, AsyncIterator[StreamChunk]]: 
            - If `stream` is False, returns a single `ChatCompletionResponse` object 
              containing the complete response.
            - If `stream` is True, returns an asynchronous iterator that yields 
              `StreamChunk` objects.

        Raises:
            APIError: If the API returns a non-200 status code or the message type is invalid.
            AuthError: If authentication fails.
            TimeoutError: If the request times out.

        Example:
            >>> stream = await client.chat.completions.create(
            >>> model="alpie-32b",
            >>> messages=[{"role": "user", "content": "Hello!"}],
            >>> stream=True,
            >>> )
            >>> async for chunk in stream:
            >>> if chunk.choices:
            >>> delta = chunk.choices[0].get("delta", {})
            >>> if delta.get("content"):
            >>> print(delta["content"], end="")

        """

        chat_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                chat_messages.append(msg)
            elif isinstance(msg, dict):
                chat_messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
            else:
                raise APIError(f"Invalid message type: {type(msg)}")

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
            return await self._create_non_streaming(request)

    async def _create_non_streaming(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Internal method to handle non-streaming chat completion requests.

        Sends a POST request to the API and parses the JSON response into a 
        ChatCompletionResponse object.

        Args:
            request (ChatCompletionRequest): The prepared request object containing 
                model parameters and messages.

        Returns:
            ChatCompletionResponse: The structured response from the API.

        Raises:
            ApiTimeoutError: If the request exceeds the client's timeout setting.
            APIError: For standard HTTP errors or unexpected exceptions.
            AuthError: If the API key is invalid.
        """
        url = f"{self.client.base_url}/chat/completions"
        headers = self.client._get_headers(stream=False)
        payload = request.to_dict()

        try:
            # Using AsyncClient context manager
            async with httpx.AsyncClient(timeout=self.client.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    self.client._handle_error_response(response)

                data = response.json()
                return ChatCompletionResponse.from_dict(data)

        except httpx.TimeoutException as e:
            raise ApiTimeoutError(str(e))

        except httpx.HTTPError as e:
            raise APIError(f"Network error: {str(e)}")

        except (AuthError, RateLimitError, APIError, ContentPolicyViolationError,
                ModelNotFoundError, ServerError, LimitExceededError, EngineOverloadedError):
            raise

        except Exception as e:
            raise APIError(f"Unexpected error: {str(e)}")

    async def _create_streaming(self, request: ChatCompletionRequest) -> AsyncIterator[StreamChunk]:
        """
        Internal method to handle streaming chat completion requests (SSE).

        Establishes a persistent connection and yields chunks of data as they 
        arrive using Server-Sent Events (SSE) format.

        Args:
            request (ChatCompletionRequest): The prepared request object.

        Yields:
            StreamChunk: A parsed chunk of the streaming response.

        Raises:
            APIError: If the stream is interrupted or contains error data.
        """
        url = f"{self.client.base_url}/chat/completions"
        headers = self.client._get_headers(stream=True)
        payload = request.to_dict()

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:

                    if response.status_code != 200:
                        await response.aread()  # Read response body asynchronously before handling error
                        self.client._handle_error_response(response)

                    async for chunk in response.aiter_text():
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
                                        message = data_json["error"].get("message", "Unknown error")
                                        raise APIError(f"Streaming error: {message}", response_data=data_json)

                                    yield StreamChunk.from_dict(data_json)

                                except json.JSONDecodeError:
                                    continue

        except httpx.TimeoutException as e:
            raise ApiTimeoutError(str(e))

        except httpx.HTTPError as e:
            raise APIError(f"Network error: {str(e)}")

        except (AuthError, RateLimitError, APIError, ContentPolicyViolationError,
                ModelNotFoundError, ServerError, EngineOverloadedError,
                LimitExceededError):
            raise

        except Exception as e:
            raise APIError(f"Unexpected streaming error: {str(e)}")