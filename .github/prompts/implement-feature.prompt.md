---
mode: agent
description: Implement one scoped feature using repository conventions and tests
---

Implement the feature described in my request. Before editing:
1. Read `.github/copilot-instructions.md`.
2. Read relevant sections of `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/DECISIONS.md`.
3. Inspect existing code, tests, configuration, and interfaces related to the feature.
4. Identify the current roadmap phase and keep the work within the requested scope.

Then:
- State a concise implementation plan.
- Reuse existing patterns and avoid unrelated refactoring.
- Implement the smallest complete change.
- Add or update tests, including relevant failure cases.
- Run the most relevant tests and report exact commands and actual outcomes.
- Update `docs/PROJECT_STATE.md` only for work evidenced by code and test results.
- Record a new accepted architecture decision in `docs/DECISIONS.md` when the change materially alters architecture.

Do not claim unrun tests passed. Do not silently change existing contracts. If a requirement conflicts with current architecture or security controls, explain the conflict before making a risky change.
