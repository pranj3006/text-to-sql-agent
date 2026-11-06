import asyncio

from text_to_sql_agent.scripts import index_schema


def test_main_awaits_indexer_and_disposes_engine(capsys):
    calls = []

    async def index_documents(engine):
        calls.append("indexed")
        return 11

    class FakeEngine:
        async def dispose(self):
            calls.append("disposed")

    asyncio.run(index_schema.main(FakeEngine(), index_documents))

    assert calls == ["indexed", "disposed"]
    assert capsys.readouterr().out == "Indexed 11 schema documents.\n"
