"""
Type definitions for the pi169 SDK.
"""

from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """Represents a chat message."""
    
    role: Literal["system", "user", "assistant"]
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for API requests."""
        return {"role": self.role, "content": self.content}


@dataclass
class Usage:
    """Token usage information."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatCompletionChoice:
    """Represents a single completion choice."""
    
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


@dataclass
class ChatCompletionResponse:
    """Response from the chat completion API."""
    
    id: str
    model: str
    choices: List[ChatCompletionChoice]
    created: int
    usage: Optional[Usage] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatCompletionResponse":
        """Create a ChatCompletionResponse from API response data."""
        choices = []
        for choice_data in data.get("choices", []):
            message_data = choice_data.get("message", {})
            message = ChatMessage(
                role=message_data.get("role", "assistant"),
                content=message_data.get("content", "")
            )
            choice = ChatCompletionChoice(
                index=choice_data.get("index", 0),
                message=message,
                finish_reason=choice_data.get("finish_reason")
            )
            choices.append(choice)
        
        usage_data = data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        ) if usage_data else None
        
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            choices=choices,
            created=data.get("created", 0),
            usage=usage
        )


@dataclass
class StreamChunk:
    """Represents a chunk from a streaming response."""
    
    id: str
    model: str
    choices: List[Dict[str, Any]]
    created: int
    delta_content: str = ""
    finish_reason: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamChunk":
        """Create a StreamChunk from streaming API data."""
        choices = data.get("choices", [])
        delta_content = ""
        finish_reason = None
        
        if choices:
            delta = choices[0].get("delta", {})
            delta_content = delta.get("content", "")
            finish_reason = choices[0].get("finish_reason")
        
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            choices=choices,
            created=data.get("created", 0),
            delta_content=delta_content,
            finish_reason=finish_reason
        )


@dataclass
class ChatCompletionRequest:
    """Request parameters for chat completion."""
    
    model: str
    messages: List[ChatMessage]
    max_tokens: int = 16384
    temperature: float = 1.0
    stream: bool = False
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "model": self.model,
            "messages": [msg.to_dict() for msg in self.messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": self.stream,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }
