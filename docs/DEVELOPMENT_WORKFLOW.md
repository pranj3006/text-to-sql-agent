# Development Workflow

## Starting a task

1. Read `.github/copilot-instructions.md`.
2. Read `docs/PROJECT_STATE.md`.
3. Read relevant architecture, database, evaluation, and ADR documentation.
4. Inspect the current code and tests.
5. Confirm the requested scope and acceptance criteria.

Treat the status document as an evidence snapshot, not as proof that a feature works. This repository currently has a prototype baseline and early scaffolding; check for package imports and initialization wiring before building on them.

## During implementation

- Make a small, reviewable change.
- Preserve existing contracts unless a change is explicitly approved.
- Add tests alongside behavior.
- Keep security controls deterministic.
- Avoid unrelated refactoring.

## Before reporting completion

- Run relevant tests.
- Report exact commands and actual outcomes.
- Distinguish implemented, tested, and verified.
- Record known limitations.
- Update project state from evidence.
- Add an ADR for material architecture changes.

The current focused test command is `uv run --no-sync pytest -q`. No database-backed or model-backed evaluation command is considered verified until it has actually been run in the configured environment. SQL bootstrap/seed files currently need to be wired into Docker initialization; do not describe the database as ready based on the Compose service alone.

## Suggested Git commit structure

- `feat: ...` for functionality
- `fix: ...` for bug fixes
- `test: ...` for tests/evaluation
- `docs: ...` for documentation
- `refactor: ...` for behavior-preserving restructuring
- `chore: ...` for tooling/configuration

Use the repository's existing commit conventions if they differ.
