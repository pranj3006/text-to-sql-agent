---
description: "Use when changing PostgreSQL schema, SQLAlchemy persistence, SQL execution, or generated-SQL validation."
applyTo:
  - "**/*.py"
  - "**/*.sql"
---

# Database standards

- PostgreSQL 17 is the target baseline unless project configuration says otherwise.
- Use SQLAlchemy 2.x APIs and explicit session lifecycle management.
- Current schema artifacts are SQL bootstrap and seed scripts under `src/text_to_sql_agent/db_scripts/`; the repository does not yet configure Alembic. Preserve that convention until a migration setup is deliberately added and documented.
- Keep database models, persistence logic, and business semantics clearly separated.
- Use parameterized statements. Never interpolate user text into SQL.
- Treat LLM-generated SQL as untrusted.
- Runtime analytics execution must use a dedicated least-privilege read-only role. The current checked-in Docker initializer does not establish one; do not assume it is enforced.
- Enforce statement timeout, row limit, allowed schemas/objects, and single-statement policy.
- Reject DML, DDL, transaction control, disallowed functions, and unauthorized objects deterministically.
- Prefer parser/AST-based validation; regex/string matching alone is insufficient.
- Do not assume a prompt instruction provides security.
- Test both allowed and rejected SQL, including comments, CTEs, nested queries, quoted identifiers, multiple statements, and bypass attempts.
- Keep business metric definitions explicit and testable; do not bury them in prompt prose.
