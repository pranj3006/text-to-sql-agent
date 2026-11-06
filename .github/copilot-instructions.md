# Copilot Instructions — Agentic Text-to-SQL

## Project

Build a testable analytics system that translates business questions into safe SQL, executes against controlled PostgreSQL data, verifies results, and returns evidence with SQL and execution metadata. Correctness, security, and measurable evaluation take priority over agent autonomy.

## Before substantial changes

Read the relevant code and project documents:

- `docs/PROJECT_STATE.md` — audited implementation and verification status; not a substitute for inspecting code.
- `docs/ARCHITECTURE.md` — target boundaries and observed wiring.
- `docs/ROADMAP.md` — phase order and current phase statuses.
- `docs/DECISIONS.md` — accepted architectural decisions.
- `docs/DATABASE_DESIGN.md` and `docs/EVALUATION.md` when changing database semantics or evaluation.

Actual code, tests, configuration, and observed command output take precedence over stale documentation. Correct directly related docs when evidence reveals drift; distinguish implemented, tested, and verified.

## Engineering and roadmap

- Follow the existing Python 3.12, FastAPI, PostgreSQL 17, SQLAlchemy, pytest, and Docker Compose conventions.
- The current baseline is a prototype. SQL schema/seed scripts are not wired into the Compose database initializer; no Alembic environment is configured.
- Keep API, application, SQL generation, validation, execution, and verification responsibilities explicit. Keep routes thin and provider-specific details replaceable.
- Use deterministic controls for authorization, SQL policy, and execution limits. Treat questions, retrieved text, model output, and database content as untrusted.
- Use the current SQL initialization convention until a deliberate, configured migration strategy replaces it. Do not infer completion from an installed dependency or scaffold.
- Follow `docs/ROADMAP.md`: stabilize database/ground truth, baseline, and evaluation before advancing retrieval or orchestration. Do not introduce MCP, LangGraph, another database, or infrastructure without a demonstrated need and scoped approval.
- Use parameterized SQL and least-privilege credentials. For generated SQL, prefer AST/parser validation, enforce an allowlist, reject writes and multiple statements, and apply database-side limits. Prompts are not security controls.
- Add proportionate tests, run the focused checks, and report exact commands and observed results. Never claim an unrun integration or evaluation succeeded.

Path-specific standards are in `.github/instructions/`; reusable task workflows are in `.github/prompts/`.
