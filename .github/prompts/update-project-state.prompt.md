---
mode: agent
description: Reconcile project progress documentation with actual repository evidence
---

Update `docs/PROJECT_STATE.md` using repository evidence.

Inspect:
- current source code and package structure
- database schema/seed scripts, models, and migrations if configured
- tests and available test output in this session
- configuration and dependency manifests
- `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/DECISIONS.md`

Rules:
1. Distinguish PROPOSED, DESIGNED, IMPLEMENTED, TESTED, and VERIFIED.
2. A file or code path existing does not prove it works.
3. Mark TESTED only when relevant tests were actually run and results are available.
4. Mark VERIFIED only when behavior and expected outcome were checked.
5. Do not infer current progress from old notes if repository evidence disagrees.
6. Preserve unresolved issues and historical context.
7. Record the exact test command and outcome when known.
8. Do not modify architecture or roadmap decisions as a side effect.
9. If evidence is missing, label the status UNKNOWN/NEEDS CONFIRMATION rather than guessing.
10. Update only the project state file unless a directly requested documentation correction is necessary.

Do not assume Alembic is configured just because it is a dependency. Inspect the actual database initialization path and test results. For this repository, distinguish the SQL bootstrap/seed files from the Compose init script that currently creates only the database and user.
