from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Interface for text embedding providers."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the configured embedding dimension."""
        raise NotImplementedError

    @abstractmethod
    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate one embedding per input, preserving input order."""
        raise NotImplementedError

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        embeddings = await self.embed_texts([text])
        return embeddings[0]