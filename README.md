# Agentic Text-to-SQL

A Python prototype for translating retail analytics questions into SQL, validating and executing read-only queries against PostgreSQL, and comparing generated results with a small golden set.

## Current status

The repository is a work in progress, not a production-ready Text-to-SQL service. The baseline, SQL initialization scripts, evaluation runner, and an experimental PostgreSQL full-text schema retriever are present. Their end-to-end behavior has not been verified. See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for the audited status and next task.

## Repository map

- `src/text_to_sql_agent/app/` — FastAPI entry point, baseline pipeline, configuration, database access, and supporting scaffolding.
- `src/text_to_sql_agent/db_scripts/` — retail schema and seed SQL.
- `src/text_to_sql_agent/evaluation/` — golden cases and baseline/reference-result runners.
- `src/text_to_sql_agent/tests/` — current unit tests.
- `.database/init/` — Docker initialization script for the database and application user; it does not currently run the schema or seed scripts.
- `docs/` — architecture, schema, roadmap, decisions, evaluation, and verified project status.
- `.github/` — Copilot instructions and reusable prompts.

## Development checks

Python 3.12 and `uv` are used by the current project configuration. Run the existing unit tests with:

```sh
uv run --no-sync pytest -q
```

The last audited run passed 4 tests. This is not an end-to-end check: no PostgreSQL-backed query run or model-backed evaluation has been verified. The Docker Compose database initialization and the SQL files under `src/text_to_sql_agent/db_scripts/` are not yet wired together as a reproducible fresh-database workflow.

## Architecture and roadmap

The intended development order is database/ground truth, baseline Text-to-SQL, evaluation, then retrieval and orchestration only when justified by measured results. Current code also contains early infrastructure scaffolding; its presence does not mean a roadmap phase is complete. See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Do not commit credentials or copy values from local environment files into documentation or source control.
