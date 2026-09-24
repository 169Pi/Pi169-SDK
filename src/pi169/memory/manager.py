from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4

from .context_builder import (
    ContextBuilder,
    DefaultContextBuilder,
)
from .embeddings import (
    EmbeddingProvider,
)
from .models import (
    Memory,
    MemoryQuery,
    MemoryResult,
    Message,
    Session,
)
from .retrieval import (
    MemoryRetriever,
)
from .storage import (
    MemoryNotFoundError,
    StorageBackend,
)
from .vector_store import (
    VectorStore,
)


class MemoryManagerError(Exception):
    """Base exception for memory manager errors."""


class MemoryManager:
    """
    Main orchestration layer for local session-based memory.

    Responsibilities:

        - manage sessions
        - persist messages
        - create memory records
        - generate embeddings
        - update FAISS
        - retrieve relevant memories
        - build model-ready context
        - rebuild the vector index
        - delete memories/sessions

    Architecture:

        MemoryManager
            │
            ├── StorageBackend
            │      └── SQLite
            │
            ├── EmbeddingProvider
            │      └── all-MiniLM-L6-v2
            │
            ├── VectorStore
            │      └── FAISS
            │
            ├── MemoryRetriever
            │
            └── ContextBuilder
    """

    def __init__(
        self,
        *,
        storage: StorageBackend,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        retriever: MemoryRetriever | None = None,
        context_builder: ContextBuilder | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.70,
        recent_messages: int = 10,
    ) -> None:
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0.0 and 1.0."
            )

        if recent_messages < 0:
            raise ValueError(
                "recent_messages cannot be negative."
            )

        if (
            embedding_provider.dimension
            != vector_store.dimension
        ):
            raise ValueError(
                "Embedding provider dimension does not match "
                "vector store dimension. "
                f"Embedding provider: "
                f"{embedding_provider.dimension}, "
                f"vector store: {vector_store.dimension}."
            )

        self._storage = storage
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

        self._top_k = top_k
        self._similarity_threshold = similarity_threshold
        self._recent_messages = recent_messages

        self._retriever = retriever or MemoryRetriever(
            storage=storage,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            default_top_k=top_k,
            default_similarity_threshold=similarity_threshold,
        )

        self._context_builder = (
            context_builder
            or DefaultContextBuilder()
        )

    # ==================================================================
    # Lifecycle
    # ==================================================================

    def initialize(self) -> None:
        """
        Initialize persistent storage and load the vector index.
        """
        self._storage.initialize()

        try:
            self._vector_store.load()
        except Exception as exc:
            raise MemoryManagerError(
                "Failed to load the memory vector index."
            ) from exc

    def close(self) -> None:
        """
        Persist the vector index and close storage.
        """
        try:
            self._vector_store.save()
        except Exception as exc:
            raise MemoryManagerError(
                "Failed to save the memory vector index."
            ) from exc
        finally:
            self._storage.close()

    # ==================================================================
    # Sessions
    # ==================================================================

    def get_or_create_session(
        self,
        session_id: str,
        *,
        metadata: dict | None = None,
    ) -> Session:
        """
        Get an existing session or create a new one.
        """
        if not session_id:
            raise ValueError(
                "session_id cannot be empty."
            )

        session = self._storage.get_session(
            session_id
        )

        if session is not None:
            return session

        now = self._now()

        session = Session(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            message_count=0,
            summary=None,
            metadata=metadata or {},
        )

        return self._storage.create_session(
            session
        )

    def get_session(
        self,
        session_id: str,
    ) -> Session | None:
        """
        Get a session without creating it.
        """
        return self._storage.get_session(
            session_id
        )

    def delete_session(
        self,
        session_id: str,
    ) -> None:
        """
        Delete a session and its associated memory vectors.
        """
        memories = self._storage.get_memories(
            session_id
        )

        memory_ids = [
            memory.id
            for memory in memories
        ]

        if memory_ids:
            self._vector_store.delete(
                memory_ids
            )

        self._storage.delete_session(
            session_id
        )

        self._vector_store.save()

    # ==================================================================
    # Messages
    # ==================================================================

    def save_message(
        self,
        message: Message,
    ) -> Message:
        """
        Persist a conversation message.

        This method stores the original conversation message only.

        It does NOT automatically create a memory. Use
        save_memory() for semantic memory persistence.
        """
        session = self._storage.get_session(
            message.session_id
        )

        if session is None:
            raise MemoryManagerError(
                f"Session '{message.session_id}' does not exist."
            )

        saved_message = self._storage.add_message(
            message
        )

        session.updated_at = self._now()
        session.message_count += 1

        self._storage.update_session(
            session
        )

        return saved_message

    def get_recent_messages(
        self,
        session_id: str,
        *,
        limit: int | None = None,
    ) -> list[Message]:
        """
        Return the most recent messages for a session.

        Messages are returned in chronological order.
        """
        limit = (
            self._recent_messages
            if limit is None
            else limit
        )

        if limit <= 0:
            return []

        messages = self._storage.get_messages(
            session_id,
            limit=limit,
        )

        return messages[-limit:]

    # ==================================================================
    # Memory creation
    # ==================================================================

    def save_memory(
        self,
        *,
        session_id: str,
        content: str,
        memory_type: str,
        source_message_id: str | None = None,
        metadata: dict | None = None,
    ) -> Memory:
        """
        Create and persist a semantic memory.

        Flow:

            text
              ↓
            SQLite
              ↓
            embedding
              ↓
            FAISS
        """
        content = content.strip()

        if not content:
            raise ValueError(
                "Memory content cannot be empty."
            )

        session = self._storage.get_session(
            session_id
        )

        if session is None:
            raise MemoryManagerError(
                f"Session '{session_id}' does not exist."
            )

        content_hash = self._content_hash(
            content
        )

        # --------------------------------------------------------------
        # Deduplication within a session
        # --------------------------------------------------------------

        existing_memories = self._storage.get_memories(
            session_id
        )

        for existing in existing_memories:
            if existing.content_hash == content_hash:
                return existing

        # --------------------------------------------------------------
        # Generate embedding
        # --------------------------------------------------------------

        try:
            embedding = (
                self._embedding_provider.embed_one(
                    content
                )
            )
        except Exception as exc:
            raise MemoryManagerError(
                "Failed to generate memory embedding."
            ) from exc

        # --------------------------------------------------------------
        # Create memory model
        # --------------------------------------------------------------

        now = self._now()

        memory = Memory(
            id=str(uuid4()),
            session_id=session_id,
            content=content,
            memory_type=memory_type,
            source_message_id=source_message_id,
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
            access_count=0,
            content_hash=content_hash,
            embedding_model=(
                self._embedding_provider.model_name
            ),
            embedding_dimension=(
                self._embedding_provider.dimension
            ),
            embedding_version=(
                self._embedding_provider.version
            ),
            metadata=metadata or {},
        )

        # --------------------------------------------------------------
        # SQLite is source of truth
        # --------------------------------------------------------------

        try:
            self._storage.add_memory(
                memory
            )
        except Exception as exc:
            raise MemoryManagerError(
                "Failed to persist memory."
            ) from exc

        # --------------------------------------------------------------
        # FAISS is derived index
        # --------------------------------------------------------------

        try:
            self._vector_store.add(
                ids=[memory.id],
                vectors=[embedding],
            )

            self._vector_store.save()

        except Exception as exc:
            # SQLite remains the source of truth. The vector index
            # can be rebuilt later.
            raise MemoryManagerError(
                "Memory was persisted, but the vector index "
                "could not be updated."
            ) from exc

        return memory

    # ==================================================================
    # Retrieval
    # ==================================================================

    def retrieve(
        self,
        *,
        session_id: str,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[MemoryResult]:
        """
        Retrieve memories relevant to a query.
        """
        if not query or not query.strip():
            return []

        session = self._storage.get_session(
            session_id
        )

        if session is None:
            raise MemoryManagerError(
                f"Session '{session_id}' does not exist."
            )

        memory_query = MemoryQuery(
            session_id=session_id,
            query=query.strip(),
            top_k=(
                self._top_k
                if top_k is None
                else top_k
            ),
            similarity_threshold=(
                self._similarity_threshold
                if similarity_threshold is None
                else similarity_threshold
            ),
        )

        return self._retriever.retrieve(
            memory_query
        )

    # ==================================================================
    # Context
    # ==================================================================

    def build_context(
        self,
        *,
        session_id: str,
        current_message: Message | None = None,
        query: str | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        recent_messages: int | None = None,
    ) -> list[dict[str, str]]:
        """
        Build model-ready context containing:

            - retrieved semantic memories
            - recent conversation
            - current user message

        The current message is NOT duplicated in recent messages.
        """
        if current_message is not None:
            if current_message.session_id != session_id:
                raise ValueError(
                    "current_message belongs to a different session."
                )

            retrieval_query = (
                query
                if query is not None
                else current_message.content
            )
        else:
            retrieval_query = query or ""

        # --------------------------------------------------------------
        # Semantic memory
        # --------------------------------------------------------------

        memories: list[MemoryResult] = []

        if retrieval_query.strip():
            memories = self.retrieve(
                session_id=session_id,
                query=retrieval_query,
                top_k=top_k,
                similarity_threshold=(
                    similarity_threshold
                ),
            )

        # --------------------------------------------------------------
        # Recent conversation
        # --------------------------------------------------------------

        message_limit = (
            self._recent_messages
            if recent_messages is None
            else recent_messages
        )

        recent = self.get_recent_messages(
            session_id,
            limit=message_limit,
        )

        # Don't duplicate the current message.
        if current_message is not None:
            recent = [
                message
                for message in recent
                if message.id != current_message.id
            ]

        # --------------------------------------------------------------
        # Build final context
        # --------------------------------------------------------------

        context = self._context_builder.build(
            memories=memories,
            recent_messages=recent,
            current_message=current_message,
        )

        return context

    # ==================================================================
    # Memory access
    # ==================================================================

    def get_memory(
        self,
        memory_id: str,
    ) -> Memory | None:
        """
        Get a memory by ID.
        """
        return self._storage.get_memory(
            memory_id
        )

    def delete_memory(
        self,
        memory_id: str,
    ) -> None:
        """
        Delete a memory from SQLite and FAISS.
        """
        memory = self._storage.get_memory(
            memory_id
        )

        if memory is None:
            raise MemoryNotFoundError(
                memory_id
            )

        # SQLite first.
        self._storage.delete_memory(
            memory_id
        )

        # Then derived vector index.
        self._vector_store.delete(
            [memory_id]
        )

        self._vector_store.save()

    def mark_memory_accessed(
        self,
        memory_id: str,
    ) -> None:
        """
        Mark one memory as accessed.
        """
        self._storage.mark_memory_accessed(
            memory_id
        )

    # ==================================================================
    # Vector index maintenance
    # ==================================================================

    def rebuild_index(
        self,
        *,
        session_id: str | None = None,
    ) -> None:
        """
        Rebuild the FAISS index from SQLite.

        SQLite is the source of truth.

        If session_id is provided, this implementation rebuilds the
        supplied session's vectors into the current index. For a
        complete index rebuild, omit session_id.
        """
        if session_id is not None:
            memories = self._storage.get_all_memories(
                session_id=session_id
            )
        else:
            memories = self._storage.get_all_memories()

        if not memories:
            if session_id is None:
                self._vector_store.clear()
                self._vector_store.save()

            return

        # --------------------------------------------------------------
        # Generate embeddings from source-of-truth SQLite content.
        # --------------------------------------------------------------

        contents = [
            memory.content
            for memory in memories
        ]

        try:
            embeddings = (
                self._embedding_provider.embed(
                    contents
                )
            )
        except Exception as exc:
            raise MemoryManagerError(
                "Failed to generate embeddings while rebuilding "
                "the vector index."
            ) from exc

        memory_ids = [
            memory.id
            for memory in memories
        ]

        # --------------------------------------------------------------
        # Full rebuild
        # --------------------------------------------------------------

        if session_id is None:
            self._vector_store.rebuild(
                ids=memory_ids,
                vectors=embeddings,
            )

            self._vector_store.save()
            return

        # --------------------------------------------------------------
        # Session-specific rebuild
        #
        # Keep existing vectors for other sessions.
        # --------------------------------------------------------------

        all_memories = self._storage.get_all_memories()

        other_memories = [
            memory
            for memory in all_memories
            if memory.session_id != session_id
        ]

        other_embeddings: list[list[float]] = []

        if other_memories:
            other_embeddings = (
                self._embedding_provider.embed(
                    [
                        memory.content
                        for memory in other_memories
                    ]
                )
            )

        combined_memories = (
            other_memories + memories
        )

        combined_embeddings = (
            other_embeddings + embeddings
        )

        combined_ids = [
            memory.id
            for memory in combined_memories
        ]

        self._vector_store.rebuild(
            ids=combined_ids,
            vectors=combined_embeddings,
        )

        self._vector_store.save()

    # ==================================================================
    # Persistence
    # ==================================================================

    def save(self) -> None:
        """
        Persist the vector index.
        """
        self._vector_store.save()

    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _now() -> datetime:
        """
        Return a timezone-aware UTC timestamp.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def _content_hash(
        content: str,
    ) -> str:
        """
        Generate a deterministic SHA-256 hash for memory content.
        """
        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()


__all__ = [
    "MemoryManager",
    "MemoryManagerError",
]