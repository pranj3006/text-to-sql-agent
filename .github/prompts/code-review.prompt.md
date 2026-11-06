---
mode: agent
description: Review changes for correctness, security, maintainability, and tests
---

Review the current changes as a senior engineer.

Prioritize findings in this order:
1. Correctness and data integrity
2. Security, authorization, and SQL safety
3. Reliability, error handling, and resource limits
4. API/data contract compatibility
5. Performance and cost
6. Maintainability and test quality

Inspect relevant project instructions and architecture docs. Report findings with severity, file/line references, impact, and a concrete fix. Distinguish confirmed defects from risks or suggestions. Do not modify code unless I explicitly ask you to fix findings. Pay special attention to generated SQL, read-only enforcement, prompt injection, retrieved content trust boundaries, and unbounded agent/tool loops.
