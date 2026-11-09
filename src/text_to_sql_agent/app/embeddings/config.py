import os
from dataclasses import dataclass
from text_to_sql_agent.app.core.config import settings

@dataclass(frozen=True)
class EmbeddingSettings:
    """Configuration for the embedding provider."""

    model: str = "text-embedding-3-small"
    dimensions: int = 1536

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("Embedding model cannot be empty.")

        if self.dimensions < 1:
            raise ValueError("Embedding dimensions must be positive.")

    @classmethod
    def from_environment(cls) -> "EmbeddingSettings":
        model = settings.EMBEDDING_MODEL
        dimensions_value = settings.EMBEDDING_DIMENSIONS

        try:
            dimensions = int(dimensions_value)
        except ValueError as exc:
            raise ValueError(
                "OPENAI_EMBEDDING_DIMENSIONS must be an integer."
            ) from exc

        return cls(model=model, dimensions=dimensions)