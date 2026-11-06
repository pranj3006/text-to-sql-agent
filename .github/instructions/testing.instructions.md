---
description: "Use when writing or changing pytest tests, database integration tests, or Text-to-SQL evaluation."
applyTo:
  - "**/tests/**"
  - "**/*test*.py"
  - "**/conftest.py"
---

# Testing standards

- Use pytest and follow existing test layout and fixtures.
- Prefer deterministic tests; mock external LLM/provider calls in unit tests.
- Use integration tests for PostgreSQL, migrations, retrieval, and MCP boundaries.
- Keep a small end-to-end suite for the complete question-to-answer flow.
- Test failure paths, timeouts, empty results, NULL values, duplicate rows, date boundaries, and malformed model output.
- Keep golden questions and independently verified expected results versioned.
- Compare result sets with explicit rules for ordering, numeric tolerance, and duplicate semantics.
- Track syntax validity separately from execution accuracy and answer correctness.
- Never mark a test as passed unless it was executed.
- Include exact commands and summarize observed results when reporting verification.
- The current suite has unit coverage for schema-document construction only; do not imply database, model, or end-to-end coverage exists without adding and running it.
