# Agentic Text-to-SQL

A Python prototype for translating retail analytics questions into SQL, executing against a read-only PostgreSQL target, and evaluating the result against independently defined reference queries. The current worktree includes a baseline FastAPI flow, a separate analytics database connection, Alembic-managed `schema_documents`, an experimental full-text/vector/hybrid schema retrieval stack, and a standalone MCP server with schema search, SQL validation, and read-only SQL execution tools.

This repository is not production-ready: database bootstrap, end-to-end query generation, and fresh benchmark validation are still unverified. The implemented retrieval and MCP pieces are useful experimental components, but they are not yet integrated as a proven end-to-end workflow.

See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for the audited current status and [docs/ROADMAP.md](docs/ROADMAP.md) for phase goals.

## Current code snapshot

- Baseline SQL generation and validation: implemented in [src/text_to_sql_agent/app/text_to_sql.py](src/text_to_sql_agent/app/text_to_sql.py)
- Application and query database split: implemented via `DATABASE_URL` and `TEXT_TO_SQL_DATABASE_URL` in [src/text_to_sql_agent/app/core/config.py](src/text_to_sql_agent/app/core/config.py)
- Schema-document corpus and Alembic migration: present under [src/text_to_sql_agent/app/rag/schema_documents.py](src/text_to_sql_agent/app/rag/schema_documents.py) and [src/text_to_sql_agent/migrations/versions/ef3a65e3fc1f_create_schema_documents.py](src/text_to_sql_agent/migrations/versions/ef3a65e3fc1f_create_schema_documents.py)
- FTS/vector/hybrid retrieval and metrics: implemented under [src/text_to_sql_agent/app/rag](src/text_to_sql_agent/app/rag) and [src/text_to_sql_agent/evaluation/rag](src/text_to_sql_agent/evaluation/rag)
- Standalone MCP server and tools: [server.py](src/text_to_sql_agent/mcp/server.py) registers `health_check`, `search_schema`, `validate_sql_tool`, and `execute_readonly_sql`; this server is not integrated into the FastAPI `/query` flow
- Query-generator golden set: present in [src/text_to_sql_agent/evaluation/query_generator/golden_cases.py](src/text_to_sql_agent/evaluation/query_generator/golden_cases.py), but the second assignment overrides the earlier case list and is not a verified production dataset

## Local quick start

Run these steps from the repository root. You need Python 3.12, [`uv`](https://docs.astral.sh/uv/), Docker with the Compose plugin, and an OpenAI API key to use `POST /query`.

1. Install the project and its locked dependencies:

   ```sh
   uv sync --locked
   ```

2. Start the local PostgreSQL 17 database:

   ```sh
   docker compose up -d postgres
   docker compose ps
   ```

   The initializer runs only when PostgreSQL first creates its data directory. Existing persisted Compose data will not automatically gain the new `app_db`/`business_db` databases or roles; preserve existing data and migrate/create the databases and roles explicitly before using the updated URLs.

3. On the first setup only, load the retail schema and seed data into `business_db`. Enable pgvector in `app_db` for schema-document embeddings, and grant the read-only business user access to the retail tables:

   ```sh
   docker compose exec -T postgres psql -U postgres -d business_db \
     < src/text_to_sql_agent/db_scripts/001_schema.sql
   docker compose exec -T postgres psql -U postgres -d business_db \
     < src/text_to_sql_agent/db_scripts/002_seed.sql
   docker compose exec postgres psql -U postgres -d app_db \
     -c 'CREATE EXTENSION IF NOT EXISTS vector;'
   docker compose exec postgres psql -U postgres -d business_db \
     -c 'REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO business_reader; GRANT SELECT ON ALL TABLES IN SCHEMA public TO business_reader; ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT ON TABLES TO business_reader;'
   ```

   The seed script is not idempotent; do not re-run these schema and seed commands on a database that already contains the tables or seed rows. Compose creates a separate `business_reader` role for the query target; the schema/table grants above enable read-only access after setup.

4. Create a root-level `.env` file with the local Compose credentials and your OpenAI key:

   ```dotenv
   DATABASE_URL=postgresql+asyncpg://app_user:<password>@localhost:5433/app_db
   TEXT_TO_SQL_DATABASE_URL=postgresql+psycopg://business_reader:<password>@localhost:5433/business_db
   TEXT_TO_SQL_SCHEMA=public
   OPENAI_API_KEY=<your-api-key>
   ```

   `DATABASE_URL` is the async application connection to `app_db`, which stores `schema_documents`. `TEXT_TO_SQL_DATABASE_URL` is the independent synchronous query connection to `business_db`, which contains the retail business data. These Compose credentials are for local development only, not production.

5. Start the API:

   ```sh
   uv run --no-sync uvicorn text_to_sql_agent.app.main:app --reload
   ```

6. In a second terminal, check the API and submit a question:

   ```sh
   curl http://127.0.0.1:8000/health
   curl -X POST http://127.0.0.1:8000/query \
     -H 'Content-Type: application/json' \
     -d '{"question":"What is net revenue by product category?"}'
   ```

The API and `/query` flow have not been verified end to end; see the setup details and known limitations below before interpreting a successful startup as proof that query generation works.

## Run the standalone MCP server

The MCP server is a separate process, not part of FastAPI startup. From the repository root, configure `DATABASE_URL` for schema-document search and `TEXT_TO_SQL_DATABASE_URL` for SQL validation/execution, then run:

```sh
uv run --no-sync python -m text_to_sql_agent.mcp.server
```

It registers four tools:

- `health_check` reports server status.
- `search_schema` runs PostgreSQL full-text search over `schema_documents`; `query` is limited to 500 characters and `limit` is 1–10 (default 5).
- `validate_sql_tool` parses and normalizes a read-only PostgreSQL query. Its allowed objects are currently hard-coded to `customers`, `products`, `orders`, and `order_items` in schema `public`.
- `execute_readonly_sql` delegates to the Text-to-SQL execution path, which reflects objects from the configured analytics database and applies its SQL validation and execution controls.

The tools have unit-test coverage, but the server has not been verified with a real MCP client, a live database, or an authorization layer. The validation tool's fixed object list can differ from the objects reflected by execution; keep this limitation in mind when configuring a target schema. See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for the audited status.

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
DATABASE_URL=postgresql+asyncpg://app_user:<password>@localhost:5433/app_db
# Independent synchronous connection used only to inspect and query analytics data:
TEXT_TO_SQL_DATABASE_URL=postgresql+psycopg://business_reader:<password>@localhost:5433/business_db
# Optional; defaults to the target database's default schema:
TEXT_TO_SQL_SCHEMA=public
# Required only for OpenAI-backed operations:
OPENAI_API_KEY=<your-api-key>
# Optional for baseline generation:
OPENAI_MODEL=<model-supported-by-your-account>
```

Both database URLs are required. `DATABASE_URL` belongs exclusively to the FastAPI application's own persistence and remains an async URL; locally it points to `app_db`, where `schema_documents` is stored. `TEXT_TO_SQL_DATABASE_URL` belongs exclusively to the Text-to-SQL query engine and must use a synchronous SQLAlchemy driver; locally it points to `business_db`, where the retail data is stored. Deployments may use different servers. The Text-to-SQL path reflects tables and views in the target schema and prompts the model using that database's SQL dialect.

The target URL can use any SQLAlchemy dialect supported by SQLGlot when its synchronous DBAPI driver is installed. For example, SQL Server can use a URL such as `mssql+pyodbc://<user>:<password>@<host>/<database>?driver=ODBC+Driver+18+for+SQL+Server`; install the matching Python DBAPI package and system database driver separately. The application database and query database each have independent SQLAlchemy engines and connection pools.

Use a dedicated read-only account for `TEXT_TO_SQL_DATABASE_URL`. The application additionally enforces a single read-only query, restricts referenced tables/views to the reflected schema, and caps returned rows. PostgreSQL queries also use a read-only transaction and statement timeout; other database servers must enforce read-only access and appropriate execution limits through their database roles and driver/server configuration.

To smoke-test the embedding API using `OPENAI_API_KEY` from the application settings:

```sh
uv run --no-sync python -m text_to_sql_agent.scripts.test_run_embeddings
```

This calls the configured embedding model and may incur API usage charges. To index the schema-document embeddings for vector or hybrid retrieval, first apply the migrations and index the schema documents as described below, then run `uv run --no-sync python -m text_to_sql_agent.scripts.index_schema_embeddings`. Both commands require `OPENAI_API_KEY`.

## Set up PostgreSQL

Start the database service:

```sh
docker compose up -d postgres
docker compose ps
```

On a fresh PostgreSQL data directory, Compose's initialization script creates `app_db` with owner `app_user` and `business_db` with the `business_reader` login role. It does **not** apply the retail schema, seed data, pgvector extension, or business-table grants. Load the retail schema and data into `business_db` as the local PostgreSQL administrator:

```sh
docker compose exec -T postgres psql -U postgres -d business_db \
  < src/text_to_sql_agent/db_scripts/001_schema.sql
docker compose exec -T postgres psql -U postgres -d business_db \
  < src/text_to_sql_agent/db_scripts/002_seed.sql
docker compose exec postgres psql -U postgres -d app_db \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
docker compose exec postgres psql -U postgres -d business_db \
  -c 'REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO business_reader; GRANT SELECT ON ALL TABLES IN SCHEMA public TO business_reader; ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT ON TABLES TO business_reader;'
```

For schema retrieval, apply the Alembic migrations to `app_db` using `app_user` or another role with DDL permissions. The app database must be enabled for pgvector as shown above.

```sh
DATABASE_URL='postgresql+asyncpg://app_user:<password>@localhost:5433/app_db' \
  uv run --no-sync alembic -c src/text_to_sql_agent/alembic.ini upgrade head
uv run --no-sync python -m text_to_sql_agent.scripts.index_schema
```

The Alembic configuration and migration files are under `src/text_to_sql_agent/` (`alembic.ini` and `migrations/`). When creating a migration from the repository root, pass the config path as well:

```sh
uv run --no-sync alembic -c src/text_to_sql_agent/alembic.ini revision --autogenerate -m "describe change"
```

Review generated migrations before applying them. Alembic manages `schema_documents` and its embedding column; retail schema/seed setup remains in the SQL scripts above. If `schema_documents` was created outside Alembic, reconcile its Alembic version state before applying the migration.

These are local-development instructions, not a production security setup. The Compose `business_reader` role is granted SELECT on the business schema during setup, but production provisioning, secret management, and least-privilege policy still require review. Seed SQL is not idempotent; do not re-run it against a database that already contains the seed rows.

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

The API startup and `/query` flow have not been verified end to end. Configure both `DATABASE_URL` for application persistence and `TEXT_TO_SQL_DATABASE_URL` for the analytics target before running the query endpoint.

## Run tests

Run retrieval unit tests without a live PostgreSQL server or external API. The settings URLs below are placeholders used only to satisfy application configuration:

```sh
DATABASE_URL='postgresql+asyncpg://user:pass@127.0.0.1/app_db' \
TEXT_TO_SQL_DATABASE_URL='sqlite:///unused.db' \
OPENAI_API_KEY='' \
uv run --no-sync pytest -q \
  src/text_to_sql_agent/tests/rag/test_hybrid_retriever.py \
  src/text_to_sql_agent/tests/rag/test_rrf.py \
  src/text_to_sql_agent/tests/rag/test_retrieval_cases.py \
  src/text_to_sql_agent/tests/rag/test_metrics.py
```

The complete suite includes a live PostgreSQL FTS retrieval test. It imports application settings and connects to the configured database, so provide both `DATABASE_URL` and `TEXT_TO_SQL_DATABASE_URL`, ensure `schema_documents` has been migrated and indexed, and grant the configured user access before running. Embedding-provider unit tests mock the external API; live vector and hybrid evaluations require `OPENAI_API_KEY`.

```sh
uv run --no-sync pytest -q
```

Passing isolated tests does not establish database, model, or end-to-end coverage. No live retrieval evaluation is run by the isolated test command.

## Run evaluations

Run the commands below from the repository root after completing the local database setup above. They use the Compose defaults shown in the quick start; replace the sample connection details if yours differ.

### Query-generator evaluation

1. Refresh the expected results by executing the independent reference SQL:

   ```sh
   DATABASE_URL='postgresql://business_reader:<password>@localhost:5433/business_db' \
     uv run --no-sync python -m text_to_sql_agent.evaluation.query_generator.run_golden
   ```

   This runner uses `psycopg.connect` directly, so pass a regular `postgresql://` URL (not the async `postgresql+asyncpg://` URL in `.env`). It writes `golden_results.json` next to the runner and overwrites the previous snapshot. Run it again when the seed data or reference SQL changes.

2. Run the model-backed dynamic-schema baseline:

   ```sh
   uv run --no-sync python -m text_to_sql_agent.evaluation.query_generator.run_baseline
   ```

   This uses `TEXT_TO_SQL_DATABASE_URL` and `OPENAI_API_KEY` from the root `.env`. It calls the configured model and runs generated and reference SQL against the query database; model usage may incur charges. It writes/overwrites `baseline_results.json`. This evaluates the baseline, not a RAG pipeline.

The active golden-case list is currently only five cases due to a duplicate assignment, and the result comparator has known ordering and numeric-tolerance limitations. Treat the baseline output as experimental.

### RAG retrieval evaluation

The retrieval evaluators require the `schema_documents` table and indexed schema documents in `app_db`. First apply the Alembic migrations as `app_user` (for an existing database, skip this if they are already applied):

```sh
DATABASE_URL='postgresql+asyncpg://app_user:<password>@localhost:5433/app_db' \
  uv run --no-sync alembic -c src/text_to_sql_agent/alembic.ini upgrade head
```

Populate/update the 11 curated schema documents in the application database:

```sh
uv run --no-sync python -m text_to_sql_agent.scripts.index_schema
```

Run the FTS benchmark (no embedding API call):

```sh
uv run --no-sync python -m text_to_sql_agent.evaluation.rag.evaluate_fts_retrieval
```

For vector or hybrid retrieval, index embeddings first:

```sh
uv run --no-sync python -m text_to_sql_agent.scripts.index_schema_embeddings
uv run --no-sync python -m text_to_sql_agent.evaluation.rag.evaluate_vector_retrieval
uv run --no-sync python -m text_to_sql_agent.evaluation.rag.evaluate_hybrid_retrieval
```

Vector and hybrid runs call the configured embedding API for each benchmark question and may incur usage charges; they do not call the chat model. The three evaluators use the same 15 retrieval cases and report Recall@k, Precision@5, MRR@10, nDCG@5, and latency. They evaluate retrieved documents, **not** whether SQL generation or final answers improve. The scripts print results but do not save a benchmark report. The repository does not yet integrate retrieval into the SQL-generation flow.

### Which evaluation should I run, and when?

| Change or milestone | Run | Why |
|---|---|---|
| Changes to deterministic metric/retrieval helpers or schema-document construction | Isolated pytest command (and the relevant focused tests) | Fast feedback without requiring the database or model |
| Schema, seed data, or reference SQL changes | `run_golden` | Re-check the independently authored expected results against the database |
| Prompt, model, or reflected-schema changes | `run_baseline` | Measure query/result behavior against the same reference set |
| FTS changes | `evaluate_fts_retrieval` | Measure full-text retrieval relevance |
| Embedding model, vector index, or vector retrieval changes | `evaluate_vector_retrieval` | Measure embedding retrieval relevance |
| RRF or hybrid retrieval changes | `evaluate_hybrid_retrieval` | Compare hybrid ranking and latency with the same cases |
| A future integrated RAG-to-SQL implementation | Run retrieval evaluation and the **same end-to-end golden set** for both baseline and RAG | Compare retrieval quality and downstream result accuracy on identical data/questions; do not claim RAG improvement from retrieval metrics alone |

The repository does not yet integrate retrieval into the SQL-generation flow, so there is currently no valid end-to-end RAG-versus-baseline evaluation command. Keep the dataset and cases fixed, save benchmark output externally if needed, and compare downstream dimensions separately (execution, result accuracy, latency, and model usage) once that integration exists.

## Project layout

- `src/text_to_sql_agent/app/` — FastAPI entry point, prototype baseline, configuration, database access, and scaffolding.
- `src/text_to_sql_agent/app/rag/` — schema-document corpus, FTS/vector/hybrid retrieval, and ranking helpers.
- `src/text_to_sql_agent/mcp/` — standalone MCP server and schema-search, SQL-validation, and read-only SQL-execution tools; not connected to FastAPI runtime.
- `src/text_to_sql_agent/db_scripts/` — retail schema and seed data for `business_db`; `schema_documents` in `app_db` is managed by Alembic.
- `src/text_to_sql_agent/evaluation/` — reference/baseline runners and experimental retrieval metrics.
- `src/text_to_sql_agent/tests/` — unit and database-dependent tests.
- `src/text_to_sql_agent/migrations/` and `src/text_to_sql_agent/alembic.ini` — Alembic migration environment and configuration.
- `docs/` — architecture, database semantics, roadmap, evaluation strategy, decisions, and audited state.

Do not commit credentials or copy values from local environment files into documentation or source control.
