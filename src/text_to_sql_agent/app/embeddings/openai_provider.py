import math

from openai import AsyncOpenAI
from text_to_sql_agent.app.core.config import settings as app_settings
from text_to_sql_agent.app.embeddings.base import EmbeddingProvider
from text_to_sql_agent.app.embeddings.config import EmbeddingSettings


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider returns invalid output."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-backed embedding provider."""

    def __init__(
        self,
        settings: EmbeddingSettings | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._settings = settings or EmbeddingSettings.from_environment()
        self._client = (
            client
            if client is not None
            else AsyncOpenAI(api_key=app_settings.OPENAI_API_KEY)
        )

    @property
    def dimensions(self) -> int:
        return self._settings.dimensions

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            raise ValueError("At least one input text is required.")

        for index, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"Input text at index {index} must be non-empty."
                )

        response = await self._client.embeddings.create(
            model=self._settings.model,
            input=texts,
            dimensions=self._settings.dimensions,
            encoding_format="float",
        )

        if len(response.data) != len(texts):
            raise EmbeddingProviderError(
                "Embedding response count does not match input count."
            )

        # The API provides an index for each input. Use it to preserve
        # the caller's input order rather than relying on response order.
        ordered_embeddings: list[list[float] | None] = [
            None
        ] * len(texts)

        for item in response.data:
            index = item.index

            if index < 0 or index >= len(texts):
                raise EmbeddingProviderError(
                    f"Unexpected embedding response index: {index}."
                )

            if ordered_embeddings[index] is not None:
                raise EmbeddingProviderError(
                    f"Duplicate embedding response index: {index}."
                )

            vector = list(item.embedding)

            if len(vector) != self.dimensions:
                raise EmbeddingProviderError(
                    "Unexpected embedding dimension: "
                    f"expected {self.dimensions}, got {len(vector)}."
                )

            if not all(
                math.isfinite(value) for value in vector
            ):
                raise EmbeddingProviderError(
                    "Embedding contains non-finite values."
                )

            ordered_embeddings[index] = vector

        if any(vector is None for vector in ordered_embeddings):
            raise EmbeddingProviderError(
                "Embedding response contains missing indices."
            )

        return [
            vector
            for vector in ordered_embeddings
            if vector is not None
        ]