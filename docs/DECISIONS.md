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
