import asyncio

from text_to_sql_agent.app.rag.vector_retriever import SchemaVectorRetriever



QUESTIONS = [
    "What is the total recognized revenue by product category?",
    "Show monthly recognized revenue trends.",
    "Which five products generated the highest recognized revenue?",
    "What is the total number of orders by customer region?",
    "Compare gross and net revenue by product category.",
]

async def main() -> None:
    retriever = SchemaVectorRetriever()

    
    for question in QUESTIONS:
        print(f"\nQuestion: {question}")

        documents = await retriever.retrieve(    
                query=question,
                limit=5,
        )

        for rank, document in enumerate(documents, start=1):
            print(
                f"{rank}. {document['document_id']} "
                f"| similarity={document['similarity']:.4f} "
                f"| {document['title']}"
            )


if __name__ == "__main__":
    asyncio.run(main())