from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from .models import MemoryResult, Message


class ContextBuilderError(Exception):
    """Raised when context construction fails."""


class ContextBuilder(ABC):
    """
    Abstract interface for building model-ready context.

    The context builder is responsible only for transforming
    already-retrieved information into model input.

    It does NOT:
        - query SQLite
        - search FAISS
        - generate embeddings
        - retrieve memories
        - call the model
        - persist messages
    """

    @abstractmethod
    def build(
        self,
        *,
        memories: Sequence[MemoryResult],
        recent_messages: Sequence[Message],
        current_message: Message | None = None,
    ) -> list[dict[str, str]]:
        """
        Build model-ready messages.

        Returns:
            A list compatible with the SDK's chat completion
            `messages` parameter.
        """
        raise NotImplementedError


class DefaultContextBuilder(ContextBuilder):
    """
    Default V1 context builder.

    Context structure:

        [memory context]
        [recent conversation]
        [current user message]

    Retrieved memories are injected separately from the actual
    conversation messages so that memory is never mistaken for
    original conversation history.
    """

    MEMORY_HEADER = (
        "The following information was retrieved from previous "
        "conversation memory. Use it only when relevant to the "
        "current request."
    )

    MEMORY_FOOTER = (
        "End of retrieved memory."
    )

    def __init__(
        self,
        *,
        memory_role: str = "system",
        include_memory_scores: bool = False,
        max_memories: int | None = None,
    ) -> None:
        if memory_role not in {
            "system",
            "user",
        }:
            raise ValueError(
                "memory_role must be either 'system' or 'user'."
            )

        if max_memories is not None and max_memories <= 0:
            raise ValueError(
                "max_memories must be greater than zero."
            )

        self._memory_role = memory_role
        self._include_memory_scores = include_memory_scores
        self._max_memories = max_memories

    def build(
        self,
        *,
        memories: Sequence[MemoryResult],
        recent_messages: Sequence[Message],
        current_message: Message | None = None,
    ) -> list[dict[str, str]]:
        """
        Build the final model-ready message list.

        Ordering:

            memory context
            ↓
            recent conversation
            ↓
            current user message
        """
        try:
            result: list[dict[str, str]] = []

            # ----------------------------------------------------------
            # 1. Retrieved memory
            # ----------------------------------------------------------

            memory_message = self._build_memory_message(
                memories
            )

            if memory_message is not None:
                result.append(memory_message)

            # ----------------------------------------------------------
            # 2. Recent conversation
            # ----------------------------------------------------------

            for message in recent_messages:
                result.append(
                    self._message_to_dict(message)
                )

            # ----------------------------------------------------------
            # 3. Current user message
            # ----------------------------------------------------------

            if current_message is not None:
                result.append(
                    self._message_to_dict(current_message)
                )

            return result

        except ContextBuilderError:
            raise

        except Exception as exc:
            raise ContextBuilderError(
                "Failed to build model context."
            ) from exc

    # ------------------------------------------------------------------
    # Memory context
    # ------------------------------------------------------------------

    def _build_memory_message(
        self,
        memories: Sequence[MemoryResult],
    ) -> dict[str, str] | None:
        """
        Convert retrieved memories into one separate context message.
        """
        if not memories:
            return None

        selected_memories = list(memories)

        if self._max_memories is not None:
            selected_memories = selected_memories[
                : self._max_memories
            ]

        if not selected_memories:
            return None

        lines: list[str] = [
            self.MEMORY_HEADER,
            "",
        ]

        for index, result in enumerate(
            selected_memories,
            start=1,
        ):
            memory = result.memory

            if self._include_memory_scores:
                lines.append(
                    f"{index}. "
                    f"{memory.content} "
                    f"(similarity={result.score:.3f})"
                )
            else:
                lines.append(
                    f"{index}. {memory.content}"
                )

        lines.extend(
            [
                "",
                self.MEMORY_FOOTER,
            ]
        )

        return {
            "role": self._memory_role,
            "content": "\n".join(lines),
        }

    # ------------------------------------------------------------------
    # Message conversion
    # ------------------------------------------------------------------

    def _message_to_dict(
        self,
        message: Message,
    ) -> dict[str, str]:
        """
        Convert an SDK Message model into the structure expected
        by the chat completion API.
        """
        role = message.role
        content = message.content

        if not role:
            raise ContextBuilderError(
                "Message role cannot be empty."
            )

        if not isinstance(content, str):
            raise ContextBuilderError(
                "Message content must be a string."
            )

        return {
            "role": role,
            "content": content,
        }


__all__ = [
    "ContextBuilder",
    "ContextBuilderError",
    "DefaultContextBuilder",
]