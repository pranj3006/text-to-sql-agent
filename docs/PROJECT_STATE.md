# Project State — Agentic Text-to-SQL

**Audited:** 2026-11-10

**Overall status:** Prototype; fresh database setup and end-to-end query behavior are not verified.

**Current focus:** Verify the local split between application persistence (`app_db`) and analytics data (`business_db`), make database initialization reproducible, and rerun retrieval/baseline evaluation before advancing the roadmap.

## Local database assignments

- `app_db` is the FastAPI application's database, configured by `DATABASE_URL`. It stores `schema_documents` and other application-owned data.
- `business_db` is the Text-to-SQL analytics target, configured by `TEXT_TO_SQL_DATABASE_URL`. It stores the retail business tables and seed data. Generated SQL and query-generator reference SQL run against this database.
- Compose provisions `app_user` for the application database and `business_reader` for the analytics database. The retail schema/data setup and business-reader grants still require the documented manual bootstrap; they have not been verified against a fresh PostgreSQL data directory.

## Objective

Translate natural-language retail analytics questions into safe SQL, execute against controlled PostgreSQL data, verify results, and return an evidence-backed answer with SQL and execution metadata.

## Current implementation

| Area | Implemented | Tested | Verified / limits |
|---|---|---|---|
| Retail database and ground truth | Retail schema, seed SQL, and query-generator reference data exist. | No fresh-database bootstrap test recorded. | Compose creates separate `app_db`/`app_user` and `business_db`/`business_reader`. It does not apply the retail schema or seed data. No fresh database setup was verified. |
| Baseline Text-to-SQL | FastAPI `/query`, reflected target schema, model SQL generation, SQLGlot validation, and separate query engine exist. | Unit coverage exists for configuration and parts of SQL generation/validation. | No live model-backed `/query` run or end-to-end result verification was performed. |
| Query-generator evaluation | Reference and model-backed evaluation runners exist. | Not freshly run against a live database in this audit. | The active golden-case module still assigns `GOLDEN_CASES` twice; the later assignment leaves five cases (Q02, Q03, Q04, Q07, Q09). Existing JSON outputs are not fresh evidence. |
| Schema document corpus | 11 curated table, relationship, and business-rule documents; Alembic migrations manage `schema_documents` and its embedding column in `app_db`. | Schema-document and migration-related unit tests exist. | Fresh migration/indexing and live database permissions were not verified in this audit. |
| Schema retrieval | PostgreSQL FTS, OpenAI embedding generation, pgvector vector retrieval, and hybrid FTS/vector retrieval with RRF are implemented. The hybrid retriever calls FTS and vector search concurrently. | Unit tests cover RRF, hybrid behavior, retrieval metrics, and benchmark-case integrity. | These are standalone experimental components. The Text-to-SQL workflow does not use them; no downstream RAG-versus-baseline result is available. |
| Retrieval evaluation | Three evaluators share 15 cases (R01–R15) and report Recall@3/5/10, Precision@5, MRR@10, nDCG@5, and latency. | Benchmark definition and metric logic are covered by unit tests. | Evaluators print to stdout and do not persist a report. A live evaluation was not run during this audit. Vector and hybrid evaluation call the embedding API. |
| MCP / LangGraph | No integration found. | — | Not started. |
| Hardening | Auth/RBAC, cache, Celery, and telemetry scaffolding exists. | Not verified as complete query-path behavior. | No production readiness or security claim is supported. |

## Recent code changes reviewed

- The retrieval benchmark in `src/text_to_sql_agent/evaluation/rag/retrieval_cases.py` now defines 15 cases, up from the five cases in the previous committed version.
- The working tree adds hybrid retrieval with Reciprocal Rank Fusion, its evaluator, and focused tests under `src/text_to_sql_agent/app/rag/`, `src/text_to_sql_agent/evaluation/rag/`, and `src/text_to_sql_agent/tests/rag/`.
- The working tree deletes `src/text_to_sql_agent/scripts/run_embeddings.py`. The current tree contains `test_run_embeddings.py` for an embedding smoke test and `index_schema_embeddings.py` for indexing document vectors; README commands now use those paths.
- These changes are still uncommitted in the current worktree. The documentation describes the current worktree, not only the last commit.

## Retrieval benchmark and current decision

The supplied progress summary reports the following comparison on the current 11-document corpus:

| Metric | FTS | Vector | Hybrid RRF |
|---|---:|---:|---:|
| Recall@3 | 0.644 | 0.622 | 0.622 |
| Recall@5 | 0.833 | 0.755 | 0.833 |
| Recall@10 | 1.000 | 1.000 | 1.000 |
| Precision@5 | 0.720 | 0.667 | 0.720 |
| MRR@10 | 0.956 | 0.967 | 1.000 |
| nDCG@5 | 0.921 | 0.890 | 0.954 |
| Mean latency (ms) | 6.88 | 433.93 | 425.10 |

These are reported values, not verified outputs: the repository contains no raw retrieval report and the benchmark was not run during this audit. They support using FTS as the preferred baseline for this corpus, while keeping vector and hybrid as experimental alternatives. This is not a default in the SQL-generation runtime, and the result should not be generalized to a larger corpus. Recall@10 is saturated at the configured top-10 limit and is not sufficiently discriminative here. See [EVALUATION.md](EVALUATION.md) for reproduction requirements and limitations.

## Documentation reconciliation

The supplied progress summary describes Phases 1–3 as completed. The checked-in implementation and previous audit evidence do not yet substantiate that completion: Compose provisions separate application (`app_db`) and analytics (`business_db`) databases but does not initialize the retail schema/seed, the baseline has not been exercised end to end, and no fresh live query-generator evaluation is recorded. Those phases remain partial/unverified until their documented exit criteria are demonstrated. Phase 4 retrieval components are implemented, but the reported benchmark is not reproducible from a checked-in artifact and retrieval is not integrated into SQL generation.

## Verification performed in this audit

- `DATABASE_URL='postgresql+asyncpg://user:pass@127.0.0.1/app_db' TEXT_TO_SQL_DATABASE_URL='sqlite:///unused.db' OPENAI_API_KEY='' uv run --no-sync pytest -q src/text_to_sql_agent/tests/rag/test_hybrid_retriever.py src/text_to_sql_agent/tests/rag/test_rrf.py src/text_to_sql_agent/tests/rag/test_retrieval_cases.py src/text_to_sql_agent/tests/rag/test_metrics.py` — **34 passed** in 1.08s. This is unit coverage; it does not connect to PostgreSQL or call the embedding API.
- A broader focused invocation including `tests/rag/test_retriever.py` yielded 38 passed and one live FTS test failure because the configured local PostgreSQL endpoint refused the connection. No live retrieval behavior is claimed as verified.
- `git diff --check` — **passed** after documentation edits.

## Known gaps and next task

- The retrieval case model has a `retrieval_query` field, but the FTS/vector/hybrid evaluators pass `question` instead. Confirm the intended benchmark input and either use or remove that unused field.
- `SchemaVectorRetriever.retrieve` is annotated as returning `list[dict]` but returns `SchemaDocument` objects; the standalone [test_vector_retriever.py](../src/text_to_sql_agent/evaluation/rag/test_vector_retriever.py) still indexes those objects as dictionaries. The main vector evaluator uses attribute access, but this probe and return type should be aligned.
- Verify Compose creates `app_db`/`app_user` and `business_db`/`business_reader` on a fresh PostgreSQL cluster. Then make setup reproducible, including ordered retail schema/seed setup in `business_db`, pgvector/schema-document migrations in `app_db`, and appropriate grants to `business_reader`. Bootstrap and grants have not been tested end to end.
- Re-run FTS/vector/hybrid evaluation with the same 15 cases; record the database/document state, embedding model, exact commands, and complete raw output in a durable report.
- Fix the query-generator golden-case override and result-comparison ordering/tolerance policy before relying on baseline metrics.
- Verify the baseline with a live database and model only after database setup is reproducible. Keep MCP and LangGraph out of scope until earlier phase exit criteria are met.

See [ROADMAP.md](ROADMAP.md) for phase status, [ARCHITECTURE.md](ARCHITECTURE.md) for observed wiring, and [DECISIONS.md](DECISIONS.md) for recorded decisions.
