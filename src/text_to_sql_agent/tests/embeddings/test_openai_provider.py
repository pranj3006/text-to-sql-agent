from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from text_to_sql_agent.app.embeddings import openai_provider
from text_to_sql_agent.app.embeddings.config import EmbeddingSettings
from text_to_sql_agent.app.embeddings.openai_provider import (
    EmbeddingProviderError,
    OpenAIEmbeddingProvider,
)


@pytest.fixture
def settings() -> EmbeddingSettings:
    return EmbeddingSettings(
        model="text-embedding-3-small",
        dimensions=3,
    )


@pytest.fixture
def mock_client() -> SimpleNamespace:
    return SimpleNamespace(
        embeddings=SimpleNamespace(
            create=AsyncMock(),
        )
    )


@pytest.fixture
def provider(
    settings: EmbeddingSettings,
    mock_client: SimpleNamespace,
) -> OpenAIEmbeddingProvider:
    return OpenAIEmbeddingProvider(
        settings=settings,
        client=mock_client,
    )


def make_embedding(index: int, values: list[float]):
    return SimpleNamespace(
        index=index,
        embedding=values,
    )


def test_provider_uses_openai_api_key_from_application_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_client_factory = Mock()
    monkeypatch.setattr(openai_provider, "AsyncOpenAI", openai_client_factory)
    monkeypatch.setattr(
        openai_provider,
        "app_settings",
        SimpleNamespace(OPENAI_API_KEY="test-api-key"),
    )

    OpenAIEmbeddingProvider(
        settings=EmbeddingSettings(model="test-model", dimensions=3)
    )

    openai_client_factory.assert_called_once_with(api_key="test-api-key")


@pytest.mark.asyncio
async def test_embed_texts_returns_vectors_in_input_order(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    # Deliberately return the embeddings out of order.
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[
            make_embedding(1, [0.4, 0.5, 0.6]),
            make_embedding(0, [0.1, 0.2, 0.3]),
        ]
    )

    result = await provider.embed_texts(
        ["first document", "second document"]
    )

    assert result == [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    mock_client.embeddings.create.assert_awaited_once_with(
        model="text-embedding-3-small",
        input=["first document", "second document"],
        dimensions=3,
        encoding_format="float",
    )


@pytest.mark.asyncio
async def test_embed_text_returns_one_vector(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[
            make_embedding(0, [0.1, 0.2, 0.3]),
        ]
    )

    result = await provider.embed_text("recognized revenue")

    assert result == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_empty_batch_is_rejected(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    with pytest.raises(ValueError, match="At least one"):
        await provider.embed_texts([])

    mock_client.embeddings.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_blank_text_is_rejected(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    with pytest.raises(ValueError, match="index 0"):
        await provider.embed_texts(["   "])

    mock_client.embeddings.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_vector_dimension_is_rejected(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[
            make_embedding(0, [0.1, 0.2]),
        ]
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="Unexpected embedding dimension",
    ):
        await provider.embed_text("recognized revenue")


@pytest.mark.asyncio
async def test_missing_response_is_rejected(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[]
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="count does not match",
    ):
        await provider.embed_text("recognized revenue")


@pytest.mark.asyncio
async def test_non_finite_values_are_rejected(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[
            make_embedding(0, [0.1, float("nan"), 0.3]),
        ]
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="non-finite",
    ):
        await provider.embed_text("recognized revenue")


@pytest.mark.asyncio
async def test_duplicate_response_index_is_rejected(
    provider: OpenAIEmbeddingProvider,
    mock_client: SimpleNamespace,
) -> None:
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[
            make_embedding(0, [0.1, 0.2, 0.3]),
            make_embedding(0, [0.4, 0.5, 0.6]),
        ]
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="Duplicate embedding response index",
    ):
        await provider.embed_texts(["first", "second"])