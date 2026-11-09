import asyncio

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.embeddings.openai_provider import (
    OpenAIEmbeddingProvider,
)


async def main() -> None:
    provider = OpenAIEmbeddingProvider()

    text = (
        "Recognized revenue includes net line value "
        "from completed orders only."
    )

    vector = await provider.embed_text(text)

    print("Embedding request succeeded.")
    print(f"Model: {settings.EMBEDDING_MODEL}")
    print(f"Dimensions: {len(vector)}")
    print(f"First 5 values: {vector[:5]}")


if __name__ == "__main__":
    asyncio.run(main())