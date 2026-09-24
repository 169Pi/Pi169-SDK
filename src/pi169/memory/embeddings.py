from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingError(Exception):
    """Raised when an embedding operation fails."""


class EmbeddingProvider(ABC):
    """Provider-agnostic interface for generating text embeddings."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the embedding model name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of generated embeddings."""
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Return a stable identifier for the embedding configuration.

        This value can be stored alongside memory records and used
        to detect incompatible embedding configurations.
        """
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: Sequence of non-empty text strings.

        Returns:
            A list of embedding vectors.
        """
        raise NotImplementedError

    def embed_one(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            A single embedding vector.
        """
        embeddings = self.embed([text])

        if not embeddings:
            raise EmbeddingError("No embedding was generated.")

        return embeddings[0]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider backed by Sentence Transformers.

    Default model:
        sentence-transformers/all-MiniLM-L6-v2

    The default model produces 384-dimensional embeddings.

    Embeddings are normalized by default. With normalized vectors,
    cosine similarity is equivalent to inner-product similarity,
    which works well with FAISS IndexFlatIP.
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_BATCH_SIZE = 32

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        device: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        normalize_embeddings: bool = True,
    ) -> None:
        if not model_name or not model_name.strip():
            raise ValueError("model_name cannot be empty.")

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self._model_name = model_name
        self._batch_size = batch_size
        self._normalize_embeddings = normalize_embeddings

        try:
            self._model = SentenceTransformer(
                model_name,
                device=device,
            )
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to load embedding model '{model_name}'."
            ) from exc

        dimension = self._model.get_sentence_embedding_dimension()

        if dimension is None:
            raise EmbeddingError(
                f"Could not determine embedding dimension for "
                f"'{model_name}'."
            )

        self._dimension = int(dimension)

        if self._dimension <= 0:
            raise EmbeddingError(
                f"Invalid embedding dimension: {self._dimension}."
            )

    @property
    def model_name(self) -> str:
        """Return the configured Sentence Transformer model name."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        return self._dimension

    @property
    def version(self) -> str:
        """
        Return a stable identifier for this embedding configuration.

        Example:
            sentence-transformers:
            model=sentence-transformers/all-MiniLM-L6-v2:
            dimension=384:
            normalized=True
        """
        return (
            "sentence-transformers"
            f":model={self._model_name}"
            f":dimension={self.dimension}"
            f":normalized={self._normalize_embeddings}"
        )

    @property
    def normalize_embeddings(self) -> bool:
        """Return whether generated embeddings are normalized."""
        return self._normalize_embeddings

    @property
    def batch_size(self) -> int:
        """Return the configured embedding batch size."""
        return self._batch_size

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts:
                A sequence of non-empty strings.

        Returns:
            A list of float vectors.

        Raises:
            ValueError:
                If the input is invalid or contains empty text.

            EmbeddingError:
                If the embedding model fails or returns invalid vectors.
        """
        if not texts:
            return []

        cleaned_texts: list[str] = []

        for text in texts:
            if not isinstance(text, str):
                raise ValueError(
                    "All texts passed to embed() must be strings."
                )

            text = text.strip()

            if not text:
                raise ValueError(
                    "Embedding text cannot be empty."
                )

            cleaned_texts.append(text)

        try:
            embeddings = self._model.encode(
                cleaned_texts,
                batch_size=self._batch_size,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to generate embeddings using "
                f"'{self._model_name}'."
            ) from exc

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        # SentenceTransformer can return a 1D vector when given
        # a single input. Convert it to the expected 2D shape.
        if embeddings.ndim == 1:
            embeddings = np.expand_dims(
                embeddings,
                axis=0,
            )

        if embeddings.ndim != 2:
            raise EmbeddingError(
                "Embedding provider returned an invalid tensor shape: "
                f"{embeddings.shape}."
            )

        if embeddings.shape[0] != len(cleaned_texts):
            raise EmbeddingError(
                "Embedding provider returned an unexpected number "
                f"of vectors. Expected {len(cleaned_texts)}, "
                f"got {embeddings.shape[0]}."
            )

        if embeddings.shape[1] != self.dimension:
            raise EmbeddingError(
                "Embedding provider returned vectors with an "
                "unexpected dimension. "
                f"Expected {self.dimension}, "
                f"got {embeddings.shape[1]}."
            )

        if not np.isfinite(embeddings).all():
            raise EmbeddingError(
                "Embedding provider returned non-finite values."
            )

        return embeddings.tolist()

    def embed_one(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text.

        This overrides the base implementation only to provide a
        stricter return-shape guarantee.
        """
        embedding = super().embed_one(text)

        if len(embedding) != self.dimension:
            raise EmbeddingError(
                "Generated embedding has an unexpected dimension. "
                f"Expected {self.dimension}, got {len(embedding)}."
            )

        return embedding


__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
]