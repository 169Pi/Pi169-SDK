from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from .models import (
    Memory,
    MemoryQuery,
    MemoryResult,
    Message,
    Session,
)


class StorageError(Exception):
    """Base exception for storage-related errors."""


class SessionNotFoundError(StorageError):
    """Raised when a requested session does not exist."""


class MessageNotFoundError(StorageError):
    """Raised when a requested message does not exist."""


class MemoryNotFoundError(StorageError):
    """Raised when a requested memory does not exist."""


class StorageBackend(ABC):
    """
    Abstract interface for persistent memory storage.

    The storage backend is responsible for:
        - sessions
        - conversation messages
        - memory records
        - metadata
        - persistence

    It must NOT be responsible for:
        - generating embeddings
        - vector similarity search
        - FAISS
        - retrieval ranking
        - context construction
        - model calls

    SQLite is the default V1 implementation.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the storage backend.

        This should create the database, tables, indexes, and
        migrations required by the backend.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close the storage backend and release resources."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    @abstractmethod
    def create_session(
        self,
        session: Session,
    ) -> Session:
        """
        Create a new session.

        Args:
            session: Session model to persist.

        Returns:
            The persisted session.
        """
        raise NotImplementedError

    @abstractmethod
    def get_session(
        self,
        session_id: str,
    ) -> Session | None:
        """
        Get a session by ID.

        Returns:
            Session if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def update_session(
        self,
        session: Session,
    ) -> Session:
        """
        Update an existing session.

        Raises:
            SessionNotFoundError:
                If the session does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_session(
        self,
        session_id: str,
    ) -> None:
        """
        Delete a session and its associated data.

        Implementations should delete associated messages and
        memories according to their database constraints.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    @abstractmethod
    def add_message(
        self,
        message: Message,
    ) -> Message:
        """
        Persist a conversation message.

        Args:
            message: Message model to persist.

        Returns:
            The persisted message.
        """
        raise NotImplementedError

    @abstractmethod
    def get_message(
        self,
        message_id: str,
    ) -> Message | None:
        """
        Get a single message by ID.

        Returns:
            Message if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_messages(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        before_sequence: int | None = None,
        after_sequence: int | None = None,
    ) -> list[Message]:
        """
        Get messages belonging to a session.

        Args:
            session_id:
                Session whose messages should be returned.

            limit:
                Optional maximum number of messages.

            before_sequence:
                Return messages before this sequence number.

            after_sequence:
                Return messages after this sequence number.

        Returns:
            Messages ordered by conversation sequence.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_message(
        self,
        message_id: str,
    ) -> None:
        """Delete a message by ID."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------------

    @abstractmethod
    def add_memory(
        self,
        memory: Memory,
    ) -> Memory:
        """
        Persist a memory record.

        Embeddings are NOT generated here.

        The memory's embedding metadata may be stored, but the
        actual vector belongs in the VectorStore.
        """
        raise NotImplementedError

    @abstractmethod
    def get_memory(
        self,
        memory_id: str,
    ) -> Memory | None:
        """
        Get a memory by ID.

        Returns:
            Memory if found, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def update_memory(
        self,
        memory: Memory,
    ) -> Memory:
        """
        Update an existing memory.

        Raises:
            MemoryNotFoundError:
                If the memory does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_memory(
        self,
        memory_id: str,
    ) -> None:
        """
        Delete a memory by ID.

        The VectorStore is responsible for removing the
        corresponding vector.
        """
        raise NotImplementedError

    @abstractmethod
    def get_memories(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        memory_type: str | None = None,
    ) -> list[Memory]:
        """
        Get memories belonging to a session.

        This is a storage/filtering operation, not semantic search.
        """
        raise NotImplementedError

    @abstractmethod
    def search_memories(
        self,
        query: MemoryQuery,
    ) -> list[MemoryResult]:
        """
        Perform metadata/storage-level memory filtering.

        IMPORTANT:
            This method should NOT perform vector similarity search.

        Semantic retrieval is handled by the retrieval layer using:

            EmbeddingProvider -> VectorStore -> StorageBackend

        This method exists for database-side filtering such as:
            - session_id
            - memory type
            - timestamps
            - metadata
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    @abstractmethod
    def get_memories_by_ids(
        self,
        memory_ids: Sequence[str],
    ) -> list[Memory]:
        """
        Fetch multiple memories by their IDs.

        This is used after FAISS returns candidate memory IDs.

        Example:

            FAISS
              ↓
            ["mem-1", "mem-7", "mem-9"]
              ↓
            get_memories_by_ids()
              ↓
            [Memory(...), Memory(...), Memory(...)]
        """
        raise NotImplementedError

    @abstractmethod
    def delete_memories_by_session(
        self,
        session_id: str,
    ) -> None:
        """
        Delete all memories belonging to a session.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_memories(
        self,
        *,
        session_id: str | None = None,
    ) -> list[Memory]:
        """
        Return all stored memories.

        This is primarily used for:
            - FAISS index rebuilding
            - maintenance
            - migrations
            - debugging

        It should not be used for normal semantic retrieval.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Memory access tracking
    # ------------------------------------------------------------------

    @abstractmethod
    def mark_memory_accessed(
        self,
        memory_id: str,
    ) -> None:
        """
        Update memory access information.

        Typical implementation:
            last_accessed_at = current timestamp
            access_count += 1
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    @abstractmethod
    def begin_transaction(self) -> None:
        """
        Begin a database transaction.
        """
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        """
        Commit the current transaction.
        """
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> StorageBackend:
        """
        Enter storage context.
        """
        self.initialize()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """
        Commit on success, rollback on failure, then close.
        """
        if exc_type is None:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
        else:
            self.rollback()

        self.close()


__all__ = [
    "StorageBackend",
    "StorageError",
    "SessionNotFoundError",
    "MessageNotFoundError",
    "MemoryNotFoundError",
]