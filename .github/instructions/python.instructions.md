---
description: Python application coding standards for this repository
applyTo: "**/*.py"
---

# Python standards
- Target Python 3.12 unless repository configuration specifies otherwise.
- Follow existing formatter, linter, and type-checker configuration. Do not add tools without a reason.
- Use type hints for public functions, methods, and data structures.
- Prefer cohesive functions and classes with explicit inputs/outputs.
- Keep domain logic independent of FastAPI, database sessions, and LLM provider SDKs where practical.
- Use dependency injection for external resources and test seams; avoid unnecessary abstractions.
- Handle expected failures explicitly. Do not use bare `except` or silently swallow exceptions.
- Use structured logging; never log secrets, credentials, raw sensitive data, or unrestricted prompts/results by default.
- Make async/sync boundaries intentional. Do not call blocking work directly from async request handlers without considering impact.
- Keep configuration in validated settings, not scattered environment lookups.
- Add tests for behavior, edge cases, and failure paths.
- Preserve established package layout and naming conventions.
