# Project State — Agentic Text-to-SQL

**Audited:** 2026-11-06
**Overall status:** Prototype; end-to-end behavior and fresh database setup remain unverified.
**Current focus:** Make database setup reproducible, fix the full-suite integration-test permissions, and separate async/sync database configuration before claiming the API or evaluations run end to end.

## Objective

Translate natural-language retail analytics questions into safe SQL, execute against controlled PostgreSQL data, verify results, and return an evidence-backed answer with SQL and execution metadata.

## Stack observed

| Area | Repository evidence |
|---|---|
| Python | Python 3.12.0 in the audit environment; `pyproject.toml` requires Python >=3.12 |
| API | FastAPI app in `src/text_to_sql_agent/app/main.py` |
| Database | PostgreSQL 17 / pgvector PostgreSQL 17 image in Docker Compose |
| Data access | SQLAlchemy sync engine in the baseline and async engine/session in the app scaffold |
| SQL parsing | SQLGlot dependency and use in the baseline validator |
| Model | OpenAI client in the baseline; configured model defaults to `gpt-5.5` in code |
| Tests | pytest; 18 collected tests including a live PostgreSQL retrieval test |
| Schema changes | SQL bootstrap/seed scripts exist; no Alembic configuration or migration files were found |
| Later-stage tools | No MCP SDK or LangGraph dependency or implementation found |

Dependency declarations are ranges; consult `uv.lock` for the lock resolution. Presence of a package or scaffold is not evidence that a feature works.

## Evidence-based implementation status

| Area | Status | Evidence and limits |
|---|---|---|
| Retail schema and seed | IMPLEMENTED as SQL files; NOT VERIFIED on a fresh database | `src/text_to_sql_agent/db_scripts/001_schema.sql` and `002_seed.sql` define tables/data. `.database/init/01-init.sh` creates a database and user but does not execute these files. |
| Baseline API and SQL generation | IMPLEMENTED as prototype; NOT END-TO-END TESTED | `/query` delegates to a static-context OpenAI generation path. The app uses an async engine while baseline execution creates a sync engine from the same `DATABASE_URL`; no model/API execution was performed in this audit. |
| SQL policy/execution | PARTIAL; NOT SECURITY-VERIFIED | SQLGlot parsing, SELECT/set-operation type checks, a function denylist, injected row cap, read-only transaction, and statement timeout are present. No object allowlist is present in this path. The checked-in DB init grants the application user all database privileges; no dedicated read-only role is defined there. |
| Golden cases | IMPLEMENTED, but effective set is unexpectedly limited | The module assigns `GOLDEN_CASES` twice. Importing it yields exactly Q02, Q03, Q04, Q07, and Q09; the earlier 12-case list is overwritten. |
| Evaluation | PARTIAL; NOT RUN AGAINST A LIVE DATABASE | Baseline and reference-result runners exist. The comparator sorts rows regardless of the declared `ORDER_SENSITIVE_CASES`, and it uses exact normalized numeric equality. Existing JSON outputs are snapshots, not fresh results from this audit. |
| Schema retrieval | EXPERIMENTAL / INCOMPLETE | Curated schema documents and PostgreSQL full-text search exist. No embedding or vector retrieval path was found. The indexing entry point awaits its async indexer, but middleware modules still contain old `app.*` imports. The live retrieval test currently fails due to database table permissions. |
| Authentication, RBAC, cache, Celery, telemetry | SCAFFOLDING; NOT VERIFIED | Related modules and dependencies exist, but these paths are not demonstrated by the query endpoint or tests. Configuration references also exceed the declared settings. |
| MCP, LangGraph, token optimization | NOT IMPLEMENTED | No project integration found. |

## Tests and checks run

- `uv run --no-sync pytest -q src/text_to_sql_agent/tests/test_metrics.py src/text_to_sql_agent/tests/test_schema_documents.py src/text_to_sql_agent/tests/test_index_schema.py` — **12 passed** in 0.42s. pytest emitted a `pytest-asyncio` deprecation warning because the default fixture loop scope is unset.
- `uv run --no-sync pytest -q` without environment settings — **collection failed** because `DATABASE_URL` and `OPENAI_API_KEY` are required during settings import.
- Full suite with local Compose-style credentials present — **17 passed, 1 failed** in 1.21s. `test_retrieve_schema_documents` reached PostgreSQL but failed with `permission denied for table schema_documents`.
- `uv run --no-sync python -m compileall -q src/text_to_sql_agent` — **passed**.
- `docker compose config --quiet` — **passed**.
- `uv run --no-sync python -c "from text_to_sql_agent.evaluation.golden_cases import GOLDEN_CASES; print(len(GOLDEN_CASES), [case['id'] for case in GOLDEN_CASES])"` — **passed**; output: `5 ['Q02', 'Q03', 'Q04', 'Q07', 'Q09']`.

The database-backed test used the existing local database; a fresh Compose initialization, schema/seed setup, API request, model call, and baseline evaluation were not run. No runtime correctness or security behavior is claimed as verified.

## Key discrepancies and limitations

- The project has moved under `src/text_to_sql_agent/`, but several support modules still import the former top-level `app` package.
- The Compose init script creates a database and user but does not apply the retail schema/seed scripts or grant the app user access to tables created by the administrator. The live retrieval test currently confirms a `schema_documents` permission failure.
- The API app uses an async SQLAlchemy engine while the baseline query path creates a separate synchronous engine and reads environment variables directly.
- The app's async and sync engines share `DATABASE_URL`, although they require different database driver URLs. The reference runner also uses `psycopg` directly and expects its own compatible DSN. The README documents current commands and limitations; the API query path still needs configuration separation.
- The standard pytest invocation needs `DATABASE_URL` and `OPENAI_API_KEY` at collection time, and the full suite includes a live database test without a unit/integration marker split.
- The README and earlier project documents described initial scaffolding rather than the current repository and have been reconciled as part of this audit.
- No production readiness, restricted database role, or end-to-end correctness claim is supported.

## Immediate next task

Make fresh PostgreSQL initialization reproducible: apply the checked-in retail schema and seed data, establish appropriate local grants and a separate least-privilege runtime query role, and add a smoke test for schema/data setup. Separate async and sync database settings so the API and evaluation tools can use compatible drivers. Then fix the duplicate golden-case override and result-comparison ordering/tolerance behavior; run reference and baseline evaluations only after the database workflow is repeatable.
