# Architecture Decision Records

Record material decisions here. Do not rewrite history; supersede an earlier decision with a new dated entry.

## ADR-0001 — Start with a deliberately small stack
- **Status:** Accepted
- **Date:** Initial project definition
- **Context:** The project is intended to teach and validate GenAI engineering while delivering a working Text-to-SQL system.
- **Decision:** Start with Python 3.12, FastAPI, PostgreSQL 17, SQLAlchemy 2.x, pytest, and Docker Compose. Introduce LangGraph, pgvector, and MCP in later phases.
- **Rationale:** A small baseline makes correctness measurable and prevents premature complexity.
- **Consequences:** Initial Text-to-SQL and evaluation should work without RAG, MCP, or agent orchestration.

## ADR-0002 — PostgreSQL as application database and initial RAG store
- **Status:** Accepted
- **Date:** Initial project definition
- **Context:** The project needs relational business data and later schema retrieval.
- **Decision:** Use PostgreSQL for the synthetic retail dataset and, in the RAG phase, pgvector plus PostgreSQL full-text search.
- **Rationale:** Reuses existing infrastructure and enables hybrid retrieval without introducing another database.
- **Consequences:** Keep relational application data and retrieval metadata logically separated through schema/table design as appropriate.

## ADR-0003 — Measure baseline before adding agentic complexity
- **Status:** Accepted
- **Date:** Initial project definition
- **Context:** RAG and agents can add cost and complexity without guaranteeing better SQL.
- **Decision:** Build a baseline and evaluation harness before Schema RAG, MCP, and LangGraph.
- **Rationale:** Improvements must be measured against a working reference.
- **Consequences:** Maintain golden questions and repeatable execution-based evaluation.

## ADR-0004 — Enforce SQL security deterministically
- **Status:** Accepted
- **Date:** Initial project definition
- **Context:** LLM-generated SQL is untrusted and prompts cannot enforce access control.
- **Decision:** Enforce read-only access, allowed objects, statement restrictions, timeouts, and row limits in application/database controls.
- **Rationale:** Security must not depend on model compliance.
- **Consequences:** SQL validation and least-privilege execution are required even in the baseline.

## ADR-0005 — Roadmap progress requires verified outcomes
- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:** The repository contains early retrieval and platform scaffolding alongside an unverified baseline and database workflow. Dependencies and files alone do not demonstrate usable capabilities.
- **Decision:** Track each roadmap phase as designed, implemented, tested, and verified separately. Do not count experimental or disconnected code as a completed phase. Stabilize database setup, baseline behavior, and evaluation before advancing to later phases.
- **Alternatives considered:** Treat presence of implementation files or dependencies as phase progress; continue implementing the next roadmap feature while baseline results remain unknown.
- **Consequences:** Schema retrieval and hardening work remain explicitly experimental/scaffolding until their entry criteria and tests are satisfied. Existing ADRs are retained as historical decisions and are not rewritten.

## ADR-0006 — Use Alembic for ORM-managed schema documents
- **Status:** Accepted
- **Date:** 2026-11-10
- **Context:** The schema-document table existed as a standalone SQL script, while Alembic was already a project dependency but had no configured environment. The user requested a SQLAlchemy model and an Alembic migration for this table.
- **Decision:** Add a SQLAlchemy model and an async PostgreSQL Alembic environment for `schema_documents`. Keep configuration in the existing `app/core/config.py`, use the shared `TimestampMixin`, keep the string `document_id` primary key, retain the existing retail schema and seed SQL, and limit Alembic autogeneration to `schema_documents` so it does not treat the non-modeled retail tables as removals.
- **Alternatives considered:** Continue managing the table only with its raw SQL script; move all retail objects into ORM models and migrations in the same change.
- **Consequences:** New schema-document setup uses `alembic upgrade head`; existing databases where the table was created by the legacy SQL script need their Alembic version state reconciled before using the migration. OpenAI credentials are optional in application settings and are checked when creating an OpenAI client. This does not yet make fresh database initialization fully reproducible.
