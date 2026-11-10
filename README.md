# Agentic Text-to-SQL

A Python prototype for translating retail analytics questions into SQL and evaluating the result against reference queries. It is not a production-ready Text-to-SQL service: database initialization, SQL execution configuration, and the experimental schema-retrieval path still have known gaps.

See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for audited implementation status and [docs/ROADMAP.md](docs/ROADMAP.md) for phase goals.

## Prerequisites

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Docker with the Compose plugin, for PostgreSQL 17 with pgvector
- An OpenAI API key for baseline query generation (the unit tests and reference-query evaluation do not call the model)

## Install

From the repository root, install the locked project dependencies and package:

```sh
uv sync --locked
```

Confirm the interpreter and package environment:

```sh
uv run python --version
```

Use `uv run ...` for the commands below so they execute in the project environment. `--no-sync` is optional when dependencies are already installed; it prevents `uv` from attempting to synchronize them.

## Configure the local environment

Create a root-level `.env` file (do not commit it) with local connection details:

```dotenv
DATABASE_URL=postgresql+asyncpg://<database-user>:<password>@localhost:5433/<database-name>
# Required only for OpenAI-backed operations:
OPENAI_API_KEY=<your-api-key>
# Optional for baseline generation:
OPENAI_MODEL=<model-supported-by-your-account>
```

The API and retrieval modules currently use an async `asyncpg` SQLAlchemy URL. The baseline generator uses a synchronous SQLAlchemy engine, while the reference runner uses `psycopg` directly; use the runner-specific URL forms in their commands below. The API also currently shares one `DATABASE_URL` between async and sync engines, so its `/query` path does not yet have a compatible single URL configuration.

To make a live embedding request using `OPENAI_API_KEY` from the application settings:

```sh
uv run --no-sync python -m text_to_sql_agent.scripts.run_embeddings
```

This calls the configured embedding model and may incur OpenAI API usage charges. An OpenAI API key is not required for database migrations or application settings that do not use an OpenAI client.

## Set up PostgreSQL

Start the database service:

```sh
docker compose up -d postgres
docker compose ps
```

On the first start, Compose's initialization script creates `app1_db` and `app1_user`, but it does **not** apply the retail schema or seed data. Apply the checked-in SQL once to a new/empty database as the local PostgreSQL administrator:

```sh
docker compose exec -T postgres psql -U postgres -d app1_db \
  < src/text_to_sql_agent/db_scripts/001_schema.sql
docker compose exec -T postgres psql -U postgres -d app1_db \
  < src/text_to_sql_agent/db_scripts/002_seed.sql
docker compose exec postgres psql -U postgres -d app1_db \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

The app database user does not automatically receive SELECT privileges on tables created by the administrator. Grant local query access:

```sh
docker compose exec postgres psql -U postgres -d app1_db \
  -c 'GRANT USAGE ON SCHEMA public TO app1_user; GRANT SELECT ON ALL TABLES IN SCHEMA public TO app1_user;'
```

For the optional schema-retrieval experiment, apply its Alembic migration using a database owner (or another role with DDL permissions), then grant the indexer access:

```sh
DATABASE_URL='postgresql+asyncpg://postgres:<password>@localhost:5433/app1_db' \
  uv run --no-sync alembic upgrade head
docker compose exec postgres psql -U postgres -d app1_db \
  -c 'GRANT SELECT, INSERT, UPDATE, DELETE ON schema_documents TO app1_user;'
```

`alembic revision --autogenerate -m "describe change"` creates future revisions from the SQLAlchemy metadata. Review generated migrations before applying them. The current migration manages `schema_documents` only; retail schema/seed setup remains in the SQL scripts above. If you already created `schema_documents` with the legacy `003_schema_documents.sql`, do not run the migration on that database without reconciling its Alembic version state first.

These are local-development instructions, not a production security setup. The current Compose initializer grants broad database privileges, and the project has not yet established a dedicated read-only execution role. Seed SQL is not idempotent; do not re-run it against a database that already contains the seed rows.

## Run the API

With the root `.env` configured and the database available:

```sh
uv run --no-sync uvicorn text_to_sql_agent.app.main:app --reload
```

In another terminal, check the health endpoint:

```sh
curl http://127.0.0.1:8000/health
```

The endpoint is `POST /query` with a JSON body such as:

```sh
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is net revenue by product category?"}'
```

The API startup and `/query` flow have not been verified end to end. In particular, `/query` currently uses a synchronous engine configured from the same `DATABASE_URL` as the async app engine; fix/separate those settings before expecting the query request to work.

## Run tests

Run isolated tests that do not need PostgreSQL or API credentials:

```sh
uv run --no-sync pytest -q \
  src/text_to_sql_agent/tests/test_metrics.py \
  src/text_to_sql_agent/tests/test_schema_documents.py \
  src/text_to_sql_agent/tests/test_index_schema.py
```

The complete suite includes a live schema-retrieval test. It imports application settings and connects to PostgreSQL, so provide `DATABASE_URL`, ensure the schema-document table exists, and grant the configured user access before running. `OPENAI_API_KEY` is needed only for tests or operations that create an OpenAI client:

```sh
uv run --no-sync pytest -q
```

The full suite currently fails in that integration test with `permission denied for table schema_documents` in the audited local database. The isolated test command is not a substitute for database integration coverage.

## Run evaluations

### 1. Refresh reference results

After schema and seed setup, execute the independent reference SQL and update `golden_results.json`:

```sh
DATABASE_URL='postgresql://<database-user>:<password>@localhost:5433/<database-name>' \
  uv run --no-sync python -m text_to_sql_agent.evaluation.query_generator.run_golden
```

Use a regular `postgresql://` DSN here because this runner calls `psycopg.connect` directly. Review the saved results when ground-truth SQL or seed data changes. The command overwrites the existing snapshot.

### 2. Measure the static-context baseline

After confirming reference results and configuring an OpenAI key, run the model-backed query evaluation:

```sh
DATABASE_URL='postgresql+psycopg://<database-user>:<password>@localhost:5433/<database-name>' \
  uv run --no-sync python -m text_to_sql_agent.evaluation.query_generator.run_baseline
```

This calls the model and executes generated and reference SQL against PostgreSQL; it may incur model charges and overwrites `baseline_results.json`. It measures the current static-schema baseline, not a RAG pipeline. The active golden-case list is currently only five cases due to a duplicate assignment, and the comparator has known ordering/tolerance limitations; treat the output as experimental until those are corrected.

### 3. Measure schema retrieval (experimental RAG component)

Create and index the schema documents first:

```sh
DATABASE_URL='postgresql+asyncpg://<database-user>:<password>@localhost:5433/<database-name>' \
  uv run --no-sync python -m text_to_sql_agent.scripts.index_schema
```

Then measure retrieval relevance:

```sh
DATABASE_URL='postgresql+asyncpg://<database-user>:<password>@localhost:5433/<database-name>' \
  uv run --no-sync python -m text_to_sql_agent.evaluation.rag.evaluate_retrieval
```

This reports retrieval metrics such as Recall@k, Precision@k, MRR, and nDCG. It evaluates which schema documents are retrieved, **not** whether generated SQL or final answers improve.

### Which evaluation should I run, and when?

| Change or milestone | Run | Why |
|---|---|---|
| Changes to deterministic metric/retrieval helpers or schema-document construction | Isolated pytest command (and the relevant focused tests) | Fast feedback without requiring the database or model |
| Schema, seed data, or reference SQL changes | `run_golden` | Re-check the independently authored expected results against the database |
| Prompt, model, or static schema-context changes | `run_baseline` | Measure query/result behavior against the same reference set |
| Schema documents, search query, ranking, or retrieval changes | `evaluate_retrieval` | Measure retrieval relevance independently of SQL generation |
| A future integrated RAG-to-SQL implementation | Run retrieval evaluation and the **same end-to-end golden set** for both baseline and RAG | Compare retrieval quality and downstream result accuracy on identical data/questions; do not claim RAG improvement from retrieval metrics alone |

The repository does not yet integrate retrieval into the SQL-generation flow, so there is currently no valid end-to-end RAG-versus-baseline evaluation command. Save the baseline report before changing the approach, keep the dataset and cases fixed, and compare dimensions separately (execution, result accuracy, latency, and model usage).

## Project layout

- `src/text_to_sql_agent/app/` — FastAPI entry point, prototype baseline, configuration, database access, and scaffolding.
- `src/text_to_sql_agent/db_scripts/` — retail schema, seed data, and schema-document SQL.
- `src/text_to_sql_agent/evaluation/` — reference/baseline runners and experimental retrieval metrics.
- `src/text_to_sql_agent/tests/` — unit and database-dependent tests.
- `docs/` — architecture, database semantics, roadmap, evaluation strategy, decisions, and audited state.

Do not commit credentials or copy values from local environment files into documentation or source control.
