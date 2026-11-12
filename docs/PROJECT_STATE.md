# Project State — Agentic Text-to-SQL

**Audited:** 2026-11-12

**Overall status:** Prototype. The baseline workflow, schema-document corpus, retrieval benchmark components, and a standalone MCP server are implemented, but fresh database bootstrap and end-to-end query verification remain unverified.

**Current focus:** Validate the local application/database split, make startup and the retail schema seed reproducible, then rerun the baseline and retrieval evaluations before claiming phase completion.

## Local database assignments

- `app_db` is the FastAPI application's database, configured by `DATABASE_URL`. It stores `schema_documents` and other application-owned data.
- `business_db` is the Text-to-SQL analytics target, configured by `TEXT_TO_SQL_DATABASE_URL`. It stores the retail business tables and seed data; generated SQL and query-generator reference SQL run against this database.
- Compose provisions separate application and analytics login roles. The retail schema/data setup and the read-only business grants still require the documented manual bootstrap and have not been verified against a fresh PostgreSQL data directory.

## Objective

Translate natural-language retail analytics questions into safe SQL, execute against controlled PostgreSQL data, verify results, and return an evidence-backed answer with SQL and execution metadata.

## Current implementation

| Area | Implemented | Tested | Verified / limits |
|---|---|---|---|
| Retail database and ground truth | Retail schema, seed SQL, and reference query definitions exist under `src/text_to_sql_agent/db_scripts/` and `evaluation/query_generator/`. | No fresh-database bootstrap test is recorded in the checked-in suite. | Compose creates separated `app_db` and `business_db`, but the retail bootstrap is still a manual step and not yet proven against a fresh cluster. |
| Baseline Text-to-SQL | FastAPI `/query`, dynamic schema reflection, model-backed SQL generation, SQLGlot validation, read-only execution, and row limiting are implemented in `app/text_to_sql.py`. | Unit tests exist for configuration and retrieval helpers; no end-to-end live query test is recorded. | The flow is implemented but not verified end to end against a live database and model. |
| Query-generator evaluation | Reference and model-backed evaluation runners exist in `evaluation/query_generator/`. | Not freshly run in this audit. | The active golden-case module assigns `GOLDEN_CASES` twice, and the later assignment overrides the earlier list. |
| Schema document corpus | 11 curated table, relationship, and business-rule documents exist, and Alembic manages `schema_documents` in `app_db`. | Schema-document and migration-related unit tests exist. | Fresh migration/indexing and live permissions have not been verified. |
| Schema retrieval | PostgreSQL FTS, OpenAI embedding generation, pgvector vector retrieval, and hybrid FTS/vector retrieval with RRF are implemented under `app/rag/`. | Unit tests cover RRF, hybrid behavior, retrieval metrics, and benchmark case integrity. | These are standalone experimental components; the SQL-generation flow does not currently call them. |
| Retrieval evaluation | Three evaluators share 15 cases (R01–R15) and report Recall@3/5/10, Precision@5, MRR@10, nDCG@5, and latency. | Benchmark definitions and metrics are covered by unit tests. | Evaluators print to stdout and do not persist a benchmark report. The live benchmark was not rerun in this audit. |
| MCP server | Standalone MCP server exists at `src/text_to_sql_agent/mcp/server.py` and exposes a `search_schema` tool. | No integration tests for MCP invocation were added in the current checked-in suite. | The server is experimental and not wired into the FastAPI request path or application startup. |
| LangGraph | No integration found. | — | Not started. |
| Hardening | Auth/RBAC, cache, Celery, and telemetry scaffolding exists. | Not verified as a complete runtime path. | No production readiness or security claim is supported. |

## Recent code changes reviewed

- `pyproject.toml` now includes `mcp[cli]`, and `src/text_to_sql_agent/mcp/server.py` adds a standalone MCP schema-search tool.
- The retrieval benchmark in `src/text_to_sql_agent/evaluation/rag/retrieval_cases.py` defines 15 cases and uses the same corpus as the RAG/document retrieval components.
- Hybrid retrieval with Reciprocal Rank Fusion and focused tests are implemented under `src/text_to_sql_agent/app/rag/`, `src/text_to_sql_agent/evaluation/rag/`, and `src/text_to_sql_agent/tests/rag/`.
- The README and docs now describe the current worktree rather than assuming all code existed in the last commit.

## Retrieval benchmark and current decision

The repository contains a 15-case retrieval benchmark, but no fresh raw benchmark report is checked in and it was not rerun during this audit. The supplied benchmark summary in the existing documentation is therefore treated as a reported result, not verified evidence.

At the code level, the current retrieval stack favors FTS as the simplest baseline for the curated 11-document corpus, while vector and hybrid recall/precision metrics remain experimental and are not wired into the SQL-generation flow. A live benchmark should be rerun with a known database state, embedding model, and exact output before using those numbers for product decisions.

## Verification performed in this audit

- `DATABASE_URL='postgresql+asyncpg://app_user:secret@127.0.0.1/app_db' TEXT_TO_SQL_DATABASE_URL='sqlite:///unused.db' OPENAI_API_KEY='' uv run --no-sync pytest -q src/text_to_sql_agent/tests/rag/test_hybrid_retriever.py src/text_to_sql_agent/tests/rag/test_rrf.py src/text_to_sql_agent/tests/rag/test_retrieval_cases.py src/text_to_sql_agent/tests/rag/test_metrics.py` — **34 passed** in 2.15s.
- `git diff --check` — **passed**.

## Known gaps and next task

- Confirm the intended retrieval benchmark input: the case model defines `retrieval_query`, but the evaluators currently pass `question` instead.
- Reconcile the duplicate `GOLDEN_CASES` assignment in `evaluation/query_generator/golden_cases.py` before using query-generator metrics as evidence.
- Verify Compose creates `app_db`/`app_user` and `business_db`/`business_reader` on a fresh PostgreSQL cluster, then make the retail schema/seed workflow reproducible and test the grants.
- Re-run the FTS/vector/hybrid evaluation with the same 15 cases and record the database/doc state, exact commands, and raw output in a durable report.
- Verify the baseline with a live database and model only after the database and security controls are reproducible, and keep MCP/LangGraph separate from the main runtime until they have clear integration scope.

See [ROADMAP.md](ROADMAP.md) for phase status, [ARCHITECTURE.md](ARCHITECTURE.md) for observed wiring, and [DECISIONS.md](DECISIONS.md) for recorded decisions.
