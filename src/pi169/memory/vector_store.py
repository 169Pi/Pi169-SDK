from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

import faiss
import numpy as np


class VectorStoreError(Exception):
    """Raised when a vector store operation fails."""


class VectorStore(ABC):
    """Provider-agnostic interface for vector storage and search."""

    @abstractmethod
    def add(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        """
        Add vectors to the store.

        Args:
            ids: Application-level IDs corresponding to each vector.
            vectors: Embedding vectors.
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        vector: Sequence[float],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """
        Search for the nearest vectors.

        Returns:
            List of (id, similarity_score) pairs.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: Sequence[str]) -> None:
        """Delete vectors by application-level ID."""
        raise NotImplementedError

    @abstractmethod
    def save(self) -> None:
        """Persist the vector index."""
        raise NotImplementedError

    @abstractmethod
    def load(self) -> None:
        """Load the vector index."""
        raise NotImplementedError

    @abstractmethod
    def rebuild(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        """Clear and rebuild the vector index."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove all vectors from the store."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return vector dimensionality."""
        raise NotImplementedError

    @property
    @abstractmethod
    def size(self) -> int:
        """Return the number of vectors in the store."""
        raise NotImplementedError


class FAISSVectorStore(VectorStore):
    """
    FAISS-backed vector store.

    Uses:
        faiss.IndexFlatIP

    IndexFlatIP performs inner-product similarity search.

    Because the embedding provider normalizes vectors, inner product
    is equivalent to cosine similarity.

    FAISS itself stores vectors, while this class maintains the mapping:

        FAISS internal ID -> application memory ID
    """

    INDEX_FILENAME = "index.faiss"
    IDS_FILENAME = "ids.npy"

    def __init__(
        self,
        dimension: int,
        storage_path: str | Path,
    ) -> None:
        if dimension <= 0:
            raise ValueError(
                "dimension must be greater than zero."
            )

        self._dimension = int(dimension)

        self._storage_path = Path(storage_path).expanduser()

        self._storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._index_path = (
            self._storage_path / self.INDEX_FILENAME
        )

        self._ids_path = (
            self._storage_path / self.IDS_FILENAME
        )

        self._index = faiss.IndexFlatIP(
            self._dimension
        )

        # Mapping:
        #
        # FAISS position -> application ID
        #
        # Example:
        #
        # 0 -> "memory-123"
        # 1 -> "memory-456"
        # 2 -> "memory-789"
        self._ids: list[str] = []

    @property
    def dimension(self) -> int:
        """Return vector dimensionality."""
        return self._dimension

    @property
    def size(self) -> int:
        """Return the number of vectors in the index."""
        return self._index.ntotal

    @property
    def storage_path(self) -> Path:
        """Return the directory containing the FAISS index."""
        return self._storage_path

    def add(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        """
        Add vectors to the FAISS index.

        Args:
            ids:
                Application-level IDs. These should normally be
                memory IDs from SQLite.

            vectors:
                Corresponding embedding vectors.

        Raises:
            ValueError:
                If IDs and vectors don't match or vectors have
                an invalid dimension.
            VectorStoreError:
                If FAISS insertion fails.
        """
        if not ids:
            return

        if len(ids) != len(vectors):
            raise ValueError(
                "The number of IDs must match the number of vectors."
            )

        for vector_id in ids:
            if not isinstance(vector_id, str):
                raise ValueError(
                    "All vector IDs must be strings."
                )

            if not vector_id:
                raise ValueError(
                    "Vector IDs cannot be empty."
                )

        matrix = self._prepare_vectors(vectors)

        try:
            self._index.add(matrix)
        except Exception as exc:
            raise VectorStoreError(
                "Failed to add vectors to FAISS."
            ) from exc

        self._ids.extend(ids)

    def search(
        self,
        vector: Sequence[float],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """
        Search for the nearest vectors.

        Args:
            vector:
                Query embedding.

            top_k:
                Maximum number of results.

        Returns:
            List of:
                (application_id, similarity_score)

        The results are ordered by descending similarity.
        """
        if top_k <= 0:
            return []

        if self.size == 0:
            return []

        query = self._prepare_query(vector)

        k = min(top_k, self.size)

        try:
            scores, indices = self._index.search(
                query,
                k,
            )
        except Exception as exc:
            raise VectorStoreError(
                "Failed to search FAISS index."
            ) from exc

        results: list[tuple[str, float]] = []

        for score, index in zip(
            scores[0],
            indices[0],
        ):
            if index < 0:
                continue

            if index >= len(self._ids):
                raise VectorStoreError(
                    "FAISS index and ID mapping are inconsistent."
                )

            results.append(
                (
                    self._ids[index],
                    float(score),
                )
            )

        return results

    def delete(
        self,
        ids: Sequence[str],
    ) -> None:
        """
        Delete vectors by application-level ID.

        FAISS IndexFlatIP does not provide efficient arbitrary
        deletion by our string IDs, so the index is rebuilt from
        the remaining vectors.

        For V1 this is acceptable because memory volumes are expected
        to be relatively small. The implementation can later be
        optimized with a different FAISS index if needed.
        """
        if not ids:
            return

        ids_to_delete = set(ids)

        if not ids_to_delete:
            return

        if not self._ids:
            return

        keep_indices = [
            index
            for index, vector_id in enumerate(self._ids)
            if vector_id not in ids_to_delete
        ]

        if len(keep_indices) == len(self._ids):
            return

        if not keep_indices:
            self.clear()
            return

        try:
            vectors = self._reconstruct_vectors(
                keep_indices
            )
        except Exception as exc:
            raise VectorStoreError(
                "Failed to reconstruct vectors while deleting IDs."
            ) from exc

        remaining_ids = [
            self._ids[index]
            for index in keep_indices
        ]

        self.rebuild(
            remaining_ids,
            vectors,
        )

    def save(self) -> None:
        """
        Persist the FAISS index and ID mapping to disk.
        """
        try:
            faiss.write_index(
                self._index,
                str(self._index_path),
            )

            np.save(
                self._ids_path,
                np.asarray(
                    self._ids,
                    dtype=np.str_,
                ),
                allow_pickle=False,
            )
        except Exception as exc:
            raise VectorStoreError(
                "Failed to save FAISS index."
            ) from exc

    def load(self) -> None:
        """
        Load the FAISS index and ID mapping from disk.

        If no persisted index exists, the store remains empty.
        """
        if not self._index_path.exists():
            return

        if not self._ids_path.exists():
            raise VectorStoreError(
                "FAISS index exists but ID mapping is missing."
            )

        try:
            index = faiss.read_index(
                str(self._index_path)
            )

            ids_array = np.load(
                self._ids_path,
                allow_pickle=False,
            )

            if index.d != self.dimension:
                raise VectorStoreError(
                    "FAISS index dimension does not match "
                    f"the configured dimension. "
                    f"Expected {self.dimension}, "
                    f"got {index.d}."
                )

            ids = ids_array.tolist()

            if index.ntotal != len(ids):
                raise VectorStoreError(
                    "FAISS index and ID mapping have different "
                    "numbers of vectors."
                )

        except VectorStoreError:
            raise

        except Exception as exc:
            raise VectorStoreError(
                "Failed to load FAISS index."
            ) from exc

        self._index = index
        self._ids = [
            str(vector_id)
            for vector_id in ids
        ]

    def rebuild(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        """
        Completely rebuild the FAISS index.

        This is intentionally supported because FAISS is a derived
        index. SQLite remains the source of truth for memory data.
        """
        if len(ids) != len(vectors):
            raise ValueError(
                "The number of IDs must match the number of vectors."
            )

        self._index = faiss.IndexFlatIP(
            self._dimension
        )

        self._ids = []

        if not ids:
            return

        self.add(
            ids,
            vectors,
        )

    def clear(self) -> None:
        """Remove all vectors from the index."""
        self._index = faiss.IndexFlatIP(
            self._dimension
        )

        self._ids = []

    def _prepare_vectors(
        self,
        vectors: Sequence[Sequence[float]],
    ) -> np.ndarray:
        """
        Convert vectors into FAISS-compatible float32 matrix.
        """
        if not vectors:
            return np.empty(
                (0, self.dimension),
                dtype=np.float32,
            )

        matrix = np.asarray(
            vectors,
            dtype=np.float32,
        )

        if matrix.ndim != 2:
            raise ValueError(
                "Vectors must be a 2-dimensional collection."
            )

        if matrix.shape[1] != self.dimension:
            raise ValueError(
                "Vector dimension mismatch. "
                f"Expected {self.dimension}, "
                f"got {matrix.shape[1]}."
            )

        if not np.isfinite(matrix).all():
            raise ValueError(
                "Vectors contain non-finite values."
            )

        return matrix

    def _prepare_query(
        self,
        vector: Sequence[float],
    ) -> np.ndarray:
        """
        Convert a single query vector into a FAISS-compatible
        2-dimensional float32 matrix.
        """
        query = np.asarray(
            vector,
            dtype=np.float32,
        )

        if query.ndim == 1:
            query = np.expand_dims(
                query,
                axis=0,
            )

        if query.ndim != 2 or query.shape[0] != 1:
            raise ValueError(
                "Query vector must contain exactly one vector."
            )

        if query.shape[1] != self.dimension:
            raise ValueError(
                "Query vector dimension mismatch. "
                f"Expected {self.dimension}, "
                f"got {query.shape[1]}."
            )

        if not np.isfinite(query).all():
            raise ValueError(
                "Query vector contains non-finite values."
            )

        return query

    def _reconstruct_vectors(
        self,
        indices: Sequence[int],
    ) -> list[list[float]]:
        """
        Reconstruct vectors from the FAISS index.

        IndexFlatIP supports exact reconstruction.
        """
        vectors: list[list[float]] = []

        for index in indices:
            vector = self._index.reconstruct(
                int(index)
            )

            vectors.append(
                vector.tolist()
            )

        return vectors


__all__ = [
    "VectorStore",
    "VectorStoreError",
    "FAISSVectorStore",
]