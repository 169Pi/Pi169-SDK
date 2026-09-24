from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from .embeddings import EmbeddingError, EmbeddingProvider
from .models import Memory, MemoryQuery, MemoryResult
from .storage import StorageBackend, StorageError
from .vector_store import VectorStore, VectorStoreError


class RetrievalError(Exception):
    """Raised when memory retrieval fails."""


class MemoryRetriever:
    """
    Semantic memory retrieval coordinator.

    Retrieval flow:

        query
          ↓
        embedding
          ↓
        FAISS
          ↓
        candidate memory IDs
          ↓
        SQLite
          ↓
        session filtering
          ↓
        similarity threshold
          ↓
        top-k results

    Responsibilities:
        - generate query embeddings
        - search the vector store
        - fetch actual memories from storage
        - enforce session isolation
        - apply similarity threshold
        - return MemoryResult objects

    This class does NOT:
        - create memories
        - persist conversation messages
        - generate memory content
        - build model context
        - call the LLM
    """

    def __init__(
        self,
        storage: StorageBackend,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        default_top_k: int = 5,
        default_similarity_threshold: float = 0.70,
    ) -> None:
        if default_top_k <= 0:
            raise ValueError(
                "default_top_k must be greater than zero."
            )

        if not 0.0 <= default_similarity_threshold <= 1.0:
            raise ValueError(
                "default_similarity_threshold must be between 0.0 and 1.0."
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

        self._default_top_k = default_top_k
        self._default_similarity_threshold = (
            default_similarity_threshold
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: MemoryQuery,
    ) -> list[MemoryResult]:
        """
        Retrieve memories relevant to a query.

        Args:
            query:
                MemoryQuery containing the query text and retrieval
                constraints.

        Returns:
            MemoryResult objects ordered by descending similarity.

        Raises:
            RetrievalError:
                If embedding, vector search, or storage access fails.
        """
        if not query.session_id:
            raise ValueError(
                "session_id is required for memory retrieval."
            )

        query_text = self._get_query_text(query)

        if not query_text:
            return []

        top_k = self._get_top_k(query)
        threshold = self._get_similarity_threshold(query)

        if top_k <= 0:
            return []

        # --------------------------------------------------------------
        # 1. Generate query embedding
        # --------------------------------------------------------------

        try:
            query_embedding = (
                self._embedding_provider.embed_one(
                    query_text
                )
            )
        except EmbeddingError as exc:
            raise RetrievalError(
                "Failed to generate query embedding."
            ) from exc

        # --------------------------------------------------------------
        # 2. Search FAISS
        # --------------------------------------------------------------

        # Search more candidates than the final top_k because we still
        # need to enforce session isolation and similarity threshold.
        candidate_k = max(
            top_k * 3,
            top_k,
        )

        try:
            candidates = self._vector_store.search(
                vector=query_embedding,
                top_k=candidate_k,
            )
        except VectorStoreError as exc:
            raise RetrievalError(
                "Failed to search vector store."
            ) from exc

        if not candidates:
            return []

        # --------------------------------------------------------------
        # 3. Apply similarity threshold
        # --------------------------------------------------------------

        candidates = [
            (memory_id, score)
            for memory_id, score in candidates
            if score >= threshold
        ]

        if not candidates:
            return []

        # --------------------------------------------------------------
        # 4. Fetch actual memory objects from SQLite
        # --------------------------------------------------------------

        memory_ids = [
            memory_id
            for memory_id, _ in candidates
        ]

        try:
            memories = self._storage.get_memories_by_ids(
                memory_ids
            )
        except StorageError as exc:
            raise RetrievalError(
                "Failed to fetch memories from storage."
            ) from exc

        if not memories:
            return []

        # --------------------------------------------------------------
        # 5. Build lookup map
        # --------------------------------------------------------------

        memory_map = {
            memory.id: memory
            for memory in memories
        }

        # --------------------------------------------------------------
        # 6. Session isolation + result construction
        # --------------------------------------------------------------

        results: list[MemoryResult] = []

        for memory_id, score in candidates:
            memory = memory_map.get(memory_id)

            if memory is None:
                # FAISS contains an ID that SQLite no longer has.
                # This can happen if the vector index is stale.
                continue

            # Mandatory V1 session isolation.
            if memory.session_id != query.session_id:
                continue

            results.append(
                MemoryResult(
                    memory=memory,
                    score=float(score),
                )
            )

            if len(results) >= top_k:
                break

        return results

    # ------------------------------------------------------------------
    # Batch retrieval
    # ------------------------------------------------------------------

    def retrieve_many(
        self,
        queries: Sequence[MemoryQuery],
    ) -> list[list[MemoryResult]]:
        """
        Retrieve memories for multiple queries.

        This method intentionally uses the normal retrieval pipeline
        for each query. Batch embedding optimization can be added
        later without changing the public API.
        """
        return [
            self.retrieve(query)
            for query in queries
        ]

    # ------------------------------------------------------------------
    # Access tracking
    # ------------------------------------------------------------------

    def mark_results_accessed(
        self,
        results: Sequence[MemoryResult],
    ) -> None:
        """
        Mark successfully retrieved memories as accessed.

        Access tracking is kept separate from retrieval so callers
        can decide whether retrieval should count as actual usage.
        """
        for result in results:
            try:
                self._storage.mark_memory_accessed(
                    result.memory.id
                )
            except StorageError as exc:
                raise RetrievalError(
                    "Failed to update memory access metadata."
                ) from exc

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _get_query_text(
        self,
        query: MemoryQuery,
    ) -> str:
        """
        Extract and normalize query text.

        V1 expects MemoryQuery to expose `query`.
        """
        text = getattr(query, "query", None)

        if text is None:
            # Compatibility with implementations that call the field
            # `text` instead of `query`.
            text = getattr(query, "text", None)

        if text is None:
            raise ValueError(
                "MemoryQuery must contain a query text."
            )

        if not isinstance(text, str):
            raise ValueError(
                "MemoryQuery query text must be a string."
            )

        return text.strip()

    def _get_top_k(
        self,
        query: MemoryQuery,
    ) -> int:
        """
        Get query-specific top_k when available, otherwise use
        the retriever default.
        """
        value = getattr(
            query,
            "top_k",
            None,
        )

        if value is None:
            return self._default_top_k

        value = int(value)

        if value <= 0:
            raise ValueError(
                "MemoryQuery.top_k must be greater than zero."
            )

        return value

    def _get_similarity_threshold(
        self,
        query: MemoryQuery,
    ) -> float:
        """
        Get query-specific similarity threshold when available,
        otherwise use the retriever default.
        """
        value = getattr(
            query,
            "similarity_threshold",
            None,
        )

        if value is None:
            return self._default_similarity_threshold

        value = float(value)

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0.0 and 1.0."
            )

        return value


__all__ = [
    "MemoryRetriever",
    "RetrievalError",
]