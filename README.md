# Agentic Text-to-SQL

A Python prototype for translating retail analytics questions into SQL and evaluating the result against reference queries. It is not a production-ready Text-to-SQL service: database initialization, SQL execution configuration, and the experimental schema-retrieval path still have known gaps.

See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for audited implementation status and [docs/ROADMAP.md](docs/ROADMAP.md) for phase goals.

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

3. On the first setup only, load the retail schema and seed data, enable pgvector, and grant the local app user read access:

   ```sh
   docker compose exec -T postgres psql -U postgres -d business_db \
     < src/text_to_sql_agent/db_scripts/001_schema.sql
   docker compose exec -T postgres psql -U postgres -d business_db \
     < src/text_to_sql_agent/db_scripts/002_seed.sql
   docker compose exec postgres psql -U postgres -d app_db \
     -c 'CREATE EXTENSION IF NOT EXISTS vector;'
   docker compose exec postgres psql -U postgres -d app_db \
     -c 'GRANT USAGE ON SCHEMA public TO app_user; GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_user;'
   ```

   The seed script is not idempotent; do not re-run these schema and seed commands on a database that already contains the tables or seed rows.

4. Create a root-level `.env` file with the local Compose credentials and your OpenAI key:

   ```dotenv
   DATABASE_URL=postgresql+asyncpg://app1_user:app1_user_password123@localhost:5433/app_db
   TEXT_TO_SQL_DATABASE_URL=postgresql+psycopg://app1_user:app1_user_password123@localhost:5433/business_db
   TEXT_TO_SQL_SCHEMA=public
   OPENAI_API_KEY=<your-api-key>
   ```

   `DATABASE_URL` is the async application connection; `TEXT_TO_SQL_DATABASE_URL` is the independent synchronous query connection. These Compose credentials are for local development only, not production.

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
DATABASE_URL=postgresql+asyncpg://<database-user>:<password>@localhost:5433/<application-database>
# Independent synchronous connection used only to inspect and query analytics data:
TEXT_TO_SQL_DATABASE_URL=postgresql+psycopg://<read-only-user>:<password>@<host>:5432/<analytics-database>
# Optional; defaults to the target database's default schema:
TEXT_TO_SQL_SCHEMA=public
# Required only for OpenAI-backed operations:
OPENAI_API_KEY=<your-api-key>
# Optional for baseline generation:
OPENAI_MODEL=<model-supported-by-your-account>
```

Both database URLs are required. `DATABASE_URL` belongs exclusively to the FastAPI application's own persistence and remains an async URL. `TEXT_TO_SQL_DATABASE_URL` belongs exclusively to the Text-to-SQL query engine and must use a synchronous SQLAlchemy driver. It may point to a different database on a different server. The Text-to-SQL path reflects tables and views in the target schema and prompts the model using that database's SQL dialect.

The target URL can use any SQLAlchemy dialect supported by SQLGlot when its synchronous DBAPI driver is installed. For example, SQL Server can use a URL such as `mssql+pyodbc://<user>:<password>@<host>/<database>?driver=ODBC+Driver+18+for+SQL+Server`; install the matching Python DBAPI package and system database driver separately. The application database and query database each have independent SQLAlchemy engines and connection pools.

Use a dedicated read-only account for `TEXT_TO_SQL_DATABASE_URL`. The application additionally enforces a single read-only query, restricts referenced tables/views to the reflected schema, and caps returned rows. PostgreSQL queries also use a read-only transaction and statement timeout; other database servers must enforce read-only access and appropriate execution limits through their database roles and driver/server configuration.

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

On the first start, Compose's initialization script creates `app_db` and `app_user`, but it does **not** apply the retail schema or seed data. Apply the checked-in SQL once to a new/empty database as the local PostgreSQL administrator:

```sh
docker compose exec -T postgres psql -U postgres -d business_db \
  < src/text_to_sql_agent/db_scripts/001_schema.sql
docker compose exec -T postgres psql -U postgres -d business_db \
  < src/text_to_sql_agent/db_scripts/002_seed.sql
docker compose exec postgres psql -U postgres -d app_db \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

The app database user does not automatically receive SELECT privileges on tables created by the administrator. Grant local query access:

```sh
docker compose exec postgres psql -U postgres -d app_db \
  -c 'GRANT USAGE ON SCHEMA public TO app1_user; GRANT SELECT ON ALL TABLES IN SCHEMA public TO app1_user;'
```

For the optional schema-retrieval experiment, apply its Alembic migration using a database owner (or another role with DDL permissions), then grant the indexer access:

```sh
DATABASE_URL='postgresql+asyncpg://postgres:<password>@localhost:5433/app_db' \
  uv run --no-sync alembic -c src/text_to_sql_agent/alembic.ini upgrade head
docker compose exec postgres psql -U postgres -d app_db \
  -c 'GRANT SELECT, INSERT, UPDATE, DELETE ON schema_documents TO app1_user;'
```

The Alembic configuration and migration files are under `src/text_to_sql_agent/` (`alembic.ini` and `migrations/`). When creating a migration from the repository root, pass the config path as well:

```sh
uv run --no-sync alembic -c src/text_to_sql_agent/alembic.ini revision --autogenerate -m "describe change"
```

Review generated migrations before applying them. The current migration manages `schema_documents` only; retail schema/seed setup remains in the SQL scripts above. If `schema_documents` was created outside Alembic, reconcile its Alembic version state before applying the migration.

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

The API startup and `/query` flow have not been verified end to end. Configure both `DATABASE_URL` for application persistence and `TEXT_TO_SQL_DATABASE_URL` for the analytics target before running the query endpoint.

## Run tests

Run isolated tests that do not need PostgreSQL or API credentials:

```sh
uv run --no-sync pytest -q \
  src/text_to_sql_agent/tests/test_metrics.py \
  src/text_to_sql_agent/tests/test_schema_documents.py \
  src/text_to_sql_agent/tests/test_index_schema.py
```

The complete suite includes a live schema-retrieval test. It imports application settings and connects to PostgreSQL, so provide both `DATABASE_URL` and `TEXT_TO_SQL_DATABASE_URL`, ensure the schema-document table exists, and grant the configured user access before running. `OPENAI_API_KEY` is needed only for tests or operations that create an OpenAI client:

```sh
uv run --no-sync pytest -q
```

The full suite currently fails in that integration test with `permission denied for table schema_documents` in the audited local database. The isolated test command is not a substitute for database integration coverage.

## Run evaluations

Run the commands below from the repository root after completing the local database setup above. They use the Compose defaults shown in the quick start; replace the sample connection details if yours differ.

### Query-generator evaluation

1. Refresh the expected results by executing the independent reference SQL:

   ```sh
   DATABASE_URL='postgresql://<database-user>:<password>@localhost:5433/<database-name>' \
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

The retrieval evaluator requires the `schema_documents` table and indexed schema documents. First apply the Alembic migration as a database owner (for an existing database, skip this if the migration is already applied):

```sh
DATABASE_URL='postgresql+asyncpg://<database-owner>:<password>@localhost:5433/<database-name>' \
  uv run --no-sync alembic -c src/text_to_sql_agent/alembic.ini upgrade head
```

Grant the local app user permission to index documents, then populate/update them:

```sh
docker compose exec postgres psql -U postgres -d app_db \
  -c 'GRANT SELECT, INSERT, UPDATE, DELETE ON schema_documents TO app1_user;'
uv run --no-sync python -m text_to_sql_agent.scripts.index_schema
```

Now run the retrieval metrics:

```sh
uv run --no-sync python -m text_to_sql_agent.evaluation.rag.evaluate_retrieval
```

This prints Recall@k, Precision@k, MRR, and nDCG metrics. It evaluates which schema documents are retrieved, **not** whether generated SQL or final answers improve, and does not call the model. The commands use `DATABASE_URL` from `.env` for indexing and retrieval, so keep it pointed at the local application database and ensure both required database URLs are configured.

### Which evaluation should I run, and when?

| Change or milestone | Run | Why |
|---|---|---|
| Changes to deterministic metric/retrieval helpers or schema-document construction | Isolated pytest command (and the relevant focused tests) | Fast feedback without requiring the database or model |
| Schema, seed data, or reference SQL changes | `run_golden` | Re-check the independently authored expected results against the database |
| Prompt, model, or reflected-schema changes | `run_baseline` | Measure query/result behavior against the same reference set |
| Schema documents, search query, ranking, or retrieval changes | `evaluate_retrieval` | Measure retrieval relevance independently of SQL generation |
| A future integrated RAG-to-SQL implementation | Run retrieval evaluation and the **same end-to-end golden set** for both baseline and RAG | Compare retrieval quality and downstream result accuracy on identical data/questions; do not claim RAG improvement from retrieval metrics alone |

The repository does not yet integrate retrieval into the SQL-generation flow, so there is currently no valid end-to-end RAG-versus-baseline evaluation command. Save the baseline report before changing the approach, keep the dataset and cases fixed, and compare dimensions separately (execution, result accuracy, latency, and model usage).

## Project layout

- `src/text_to_sql_agent/app/` — FastAPI entry point, prototype baseline, configuration, database access, and scaffolding.
- `src/text_to_sql_agent/db_scripts/` — retail schema, seed data, and schema-document SQL.
- `src/text_to_sql_agent/evaluation/` — reference/baseline runners and experimental retrieval metrics.
- `src/text_to_sql_agent/tests/` — unit and database-dependent tests.
- `src/text_to_sql_agent/migrations/` and `src/text_to_sql_agent/alembic.ini` — Alembic migration environment and configuration.
- `docs/` — architecture, database semantics, roadmap, evaluation strategy, decisions, and audited state.

Do not commit credentials or copy values from local environment files into documentation or source control.
