# Project State — Agentic Text-to-SQL

**Audited:** 2026-11-10
**Overall status:** Prototype; end-to-end behavior and fresh database setup remain unverified.
**Current focus:** Make database setup reproducible, fix the full-suite integration-test permissions, and verify the newly separated application/query database connections end to end.

## Objective

Translate natural-language retail analytics questions into safe SQL, execute against controlled PostgreSQL data, verify results, and return an evidence-backed answer with SQL and execution metadata.

## Stack observed

| Area | Repository evidence |
|---|---|
| Python | Python 3.12.0 in the audit environment; `pyproject.toml` requires Python >=3.12 |
| API | FastAPI app in `src/text_to_sql_agent/app/main.py` |
| Database | PostgreSQL 17 / pgvector PostgreSQL 17 image in Docker Compose |
| Data access | Async SQLAlchemy engine/session for app persistence; independent synchronous engine for the Text-to-SQL target |
| SQL parsing | SQLGlot parses and serializes SQL using the reflected target dialect |
| Model | OpenAI client in the baseline; configured model defaults to `gpt-5.5` in code |
| Tests | pytest; unit tests plus a live PostgreSQL retrieval test |
| Schema changes | Retail bootstrap/seed SQL remains; `schema_documents` now has a SQLAlchemy model and Alembic migration |
| Later-stage tools | No MCP SDK or LangGraph dependency or implementation found |

Dependency declarations are ranges; consult `uv.lock` for the lock resolution. Presence of a package or scaffold is not evidence that a feature works.

## Evidence-based implementation status

| Area | Status | Evidence and limits |
|---|---|---|
| Schema-document persistence | IMPLEMENTED; MODEL TESTED; MIGRATION NOT APPLIED | `app/db/models.py`, `migrations/env.py`, and `migrations/versions/ef3a65e3fc1f_create_schema_documents.py` define the model and migration. PostgreSQL offline SQL generation succeeded; no `DATABASE_URL` was available to apply it to a live database. Alembic autogeneration is limited to `schema_documents`; retail tables remain SQL-managed. |
| Retail schema and seed | IMPLEMENTED as SQL files; NOT VERIFIED on a fresh database | `src/text_to_sql_agent/db_scripts/001_schema.sql` and `002_seed.sql` define tables/data. `.database/init/01-init.sh` creates a database and user but does not execute these files. |
| Baseline API and SQL generation | IMPLEMENTED as prototype; NOT END-TO-END TESTED | `/query` reflects tables/views from required `TEXT_TO_SQL_DATABASE_URL` and prompts using its SQL dialect. Required `DATABASE_URL` remains the async application persistence connection. No model/API execution was performed. |
| SQL policy/execution | PARTIAL; NOT SECURITY-VERIFIED | SQLGlot parsing, SELECT/set-operation checks, a function denylist, a reflected table/view allowlist, and a 100-row cap are present. PostgreSQL execution uses a read-only transaction and timeout; SQLite uses query-only mode. Other backends require server/driver read-only permissions and execution limits; columns are not individually allowlisted. No dedicated read-only role is configured in the checked-in database init. |
| Golden cases | IMPLEMENTED, but effective set is unexpectedly limited | The module assigns `GOLDEN_CASES` twice. Importing it yields exactly Q02, Q03, Q04, Q07, and Q09; the earlier 12-case list is overwritten. |
| Evaluation | PARTIAL; NOT RUN AGAINST A LIVE DATABASE | Baseline and reference-result runners exist. The comparator sorts rows regardless of the declared `ORDER_SENSITIVE_CASES`, and it uses exact normalized numeric equality. Existing JSON outputs are snapshots, not fresh results from this audit. |
| Schema retrieval | EXPERIMENTAL / INCOMPLETE | Curated schema documents and PostgreSQL full-text search exist. No embedding or vector retrieval path was found. The indexing entry point awaits its async indexer, but middleware modules still contain old `app.*` imports. The live retrieval test currently fails due to database table permissions. |
| Authentication, RBAC, cache, Celery, telemetry | SCAFFOLDING; NOT VERIFIED | Related modules and dependencies exist, but these paths are not demonstrated by the query endpoint or tests. Configuration references also exceed the declared settings. |
| MCP, LangGraph, token optimization | NOT IMPLEMENTED | No project integration found. |

## Tests and checks run

- `DATABASE_URL='postgresql+asyncpg://test:test@localhost/test' env -u OPENAI_API_KEY uv run --no-sync pytest -q src/text_to_sql_agent/tests/test_config.py src/text_to_sql_agent/tests/test_schema_document_model.py src/text_to_sql_agent/tests/embeddings/test_openai_provider.py src/text_to_sql_agent/tests/test_schema_documents.py src/text_to_sql_agent/tests/test_index_schema.py src/text_to_sql_agent/tests/rag/test_metrics.py` — **26 passed** in 1.15s; only the existing `pytest-asyncio` fixture-loop deprecation warning was emitted.
- `DATABASE_URL='postgresql+asyncpg://test:test@localhost/test' env -u OPENAI_API_KEY uv run --no-sync alembic upgrade head --sql` — **passed**, rendering PostgreSQL DDL without an OpenAI key or live connection.
- `uv run --no-sync python -m compileall -q src/text_to_sql_agent migrations` and `git diff --check` — **passed**.
- `DATABASE_URL='postgresql+asyncpg://migration_user:placeholder@localhost/example_db' uv run --no-sync alembic upgrade head --sql` — **passed**; emitted PostgreSQL DDL for the table, generated search vector, category index, and one GIN index. This rendered SQL only; it did not connect to or alter a database.
- `git diff --check` — **passed** after implementation.
- `uv run --no-sync pytest -q src/text_to_sql_agent/tests/test_metrics.py src/text_to_sql_agent/tests/test_schema_documents.py src/text_to_sql_agent/tests/test_index_schema.py` — **12 passed** in 0.42s. pytest emitted a `pytest-asyncio` deprecation warning because the default fixture loop scope is unset.
- `uv run --no-sync pytest -q` without environment settings — **collection failed** because `DATABASE_URL` and `OPENAI_API_KEY` are required during settings import.
- Full suite with local Compose-style credentials present — **17 passed, 1 failed** in 1.21s. `test_retrieve_schema_documents` reached PostgreSQL but failed with `permission denied for table schema_documents`.
- `uv run --no-sync python -m compileall -q src/text_to_sql_agent` — **passed**.
- `docker compose config --quiet` — **passed**.
- `uv run --no-sync python -c "from text_to_sql_agent.evaluation.golden_cases import GOLDEN_CASES; print(len(GOLDEN_CASES), [case['id'] for case in GOLDEN_CASES])"` — **passed**; output: `5 ['Q02', 'Q03', 'Q04', 'Q07', 'Q09']`.
- `DATABASE_URL='postgresql+asyncpg://app/app_db' env -u OPENAI_API_KEY uv run --no-sync pytest -q src/text_to_sql_agent/tests/test_config.py src/text_to_sql_agent/tests/test_text_to_sql.py` — **8 passed** in 1.28s. This covers separate/optional URL configuration, SQLite schema reflection and read-only mode reset, table allowlisting, result row cap, and SQL Server dialect parsing/serialization; it does not connect to SQL Server or call a model.
- `DATABASE_URL='postgresql+asyncpg://app/app_db' TEXT_TO_SQL_DATABASE_URL='sqlite:///analytics.db' env -u OPENAI_API_KEY uv run --no-sync pytest -q src/text_to_sql_agent/tests/test_config.py src/text_to_sql_agent/tests/test_text_to_sql.py src/text_to_sql_agent/tests/test_schema_document_model.py src/text_to_sql_agent/tests/embeddings/test_openai_provider.py src/text_to_sql_agent/tests/test_schema_documents.py src/text_to_sql_agent/tests/test_index_schema.py src/text_to_sql_agent/tests/rag/test_metrics.py` — **35 passed** in 1.55s after making both database URLs required. The new tests use SQLite and mock the model; no external SQL Server or model service was contacted.
- `git diff --check` — **passed** after the external-database change.

The database-backed test used the existing local database; a fresh Compose initialization, schema/seed setup, API request, model call, and baseline evaluation were not run. No runtime correctness or security behavior is claimed as verified.

## Key discrepancies and limitations

- The project has moved under `src/text_to_sql_agent/`, but several support modules still import the former top-level `app` package.
- Alembic currently manages only `schema_documents`; retail tables and seeds are still managed by SQL scripts. The new migration has not been applied to a live database.
- The Compose init script creates a database and user but does not apply the retail schema/seed scripts or grant the app user access to tables created by the administrator. The live retrieval test currently confirms a `schema_documents` permission failure.
- The API app uses an async SQLAlchemy engine from `DATABASE_URL`. The query workflow lazily creates its own synchronous engine from `TEXT_TO_SQL_DATABASE_URL`; it does not fall back to the application connection. A synchronous DBAPI driver compatible with the target SQLAlchemy dialect must be installed. The baseline evaluation continues to use its PostgreSQL retail reference queries.
- Both `DATABASE_URL` and `TEXT_TO_SQL_DATABASE_URL` are required when application settings are imported; the full suite includes a live database test without a unit/integration marker split. `OPENAI_API_KEY` is optional at settings load and required only when creating an OpenAI client.
- The README and earlier project documents described initial scaffolding rather than the current repository and have been reconciled as part of this audit.
- No production readiness, restricted database role, or end-to-end correctness claim is supported.

## Immediate next task

Make fresh PostgreSQL initialization reproducible: apply the checked-in retail schema and seed data, establish appropriate local grants and a separate least-privilege runtime query role, and add a smoke test for schema/data setup. Add or confirm target-specific column/statement limits and integration-test the Text-to-SQL path against a live PostgreSQL target and a SQL Server target when available. Then fix the duplicate golden-case override and result-comparison ordering/tolerance behavior; run reference and baseline evaluations only after the database workflow is repeatable.
