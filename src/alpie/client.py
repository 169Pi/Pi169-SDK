"""
Main client class for the Alpie SDK.
"""

import json
from typing import Iterator, Optional, Union, List
import httpx

from alpie.exceptions import (
    APIError,
    AuthError,
    RateLimitError,
    TimeoutError as AlpieTimeoutError,
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
    StreamChunk,
)


class Alpie:
    """Main client for interacting with the Alpie API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.169pi.com/v1",
        timeout: float = 60.0,
        max_retries: int = 2,
    ):
        if not api_key:
            raise AuthError("API key is required")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.chat = ChatCompletions(self)

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
            message = error_info.get("message", "Unknown error")
            error_type = error_info.get("type", "unknown")
        else:
            message = str(error_info)
            error_type = "unknown"

        status_code = response.status_code

        # ---------------------
        # Status-Code Based Mapping
        # ---------------------

        if status_code == 401:
            raise AuthError(message, status_code, error_data)

        if status_code == 400:
            # multiple possible API-level subtypes
            if error_type == "content_policy_violation":
                raise ContentPolicyViolationError(message, status_code, error_data)
            elif error_type == "context_window_exceeded":
                raise ContextWindowExceededError(message, status_code, error_data)
            elif error_type == "unsupported_params":
                raise UnsupportedParamsError(message, status_code, error_data)
            else:
                raise APIError(message, status_code, error_data)

        if status_code == 402:
            raise LimitExceededError(message, status_code, error_data)

        if status_code == 403:
            raise ContentPolicyViolationError(message, status_code, error_data)

        if status_code == 404:
            raise ModelNotFoundError(message, status_code, error_data)

        if status_code == 429:
            raise RateLimitError(message, status_code, error_data)

        if status_code == 503:
            raise EngineOverloadedError(message, status_code, error_data)

        if status_code == 504:
            raise AlpieTimeoutError(message, status_code, error_data)

        if 500 <= status_code <= 599:
            raise ServerError(f"Server error {status_code}: {message}", status_code, error_data)

        # Fallback for everything else
        raise APIError(f"API error {status_code}: {message}", status_code, error_data)



class ChatCompletions:
    """Handler for chat completion endpoints."""

    def __init__(self, client: Alpie):
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

        return (
            self._create_streaming(request)
            if stream
            else self._create_non_streaming(request)
        )

    def _create_non_streaming(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
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
            raise AlpieTimeoutError(str(e))

        except httpx.HTTPError as e:
            raise APIError(f"Network error: {str(e)}")

        except (AuthError, RateLimitError, APIError, ContentPolicyViolationError,
                ModelNotFoundError, ServerError, LimitExceededError, EngineOverloadedError):
            raise

        except Exception as e:
            raise APIError(f"Unexpected error: {str(e)}")

    def _create_streaming(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
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
                                        message = data_json["error"].get("message", "Unknown error")
                                        raise APIError(f"Streaming error: {message}", response_data=data_json)

                                    yield StreamChunk.from_dict(data_json)

                                except json.JSONDecodeError:
                                    continue

        except httpx.TimeoutException as e:
            raise AlpieTimeoutError(str(e))

        except httpx.HTTPError as e:
            raise APIError(f"Network error: {str(e)}")

        except (AuthError, RateLimitError, APIError, ContentPolicyViolationError,
                ModelNotFoundError, ServerError, EngineOverloadedError,
                LimitExceededError):
            raise

        except Exception as e:
            raise APIError(f"Unexpected streaming error: {str(e)}")
