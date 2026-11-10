# Development Roadmap

Progress is updated only when supported by repository and test evidence. Statuses below reflect the repository audit on 2026-11-10; they are not claims of successful end-to-end behavior.

## Audited status summary

| Phase | Status | Evidence-based summary |
|---|---|---|
| 01 — Database and ground truth | PARTIAL / NOT VERIFIED | Retail schema and seed SQL exist, but Compose initialization does not execute them. Alembic manages `schema_documents`, not the retail tables. No fresh-database test or verified database run was found. |
| 02 — Baseline Text-to-SQL | PROTOTYPE / NOT END-TO-END TESTED | FastAPI route, reflected target schema, dialect-aware generation, SQLGlot validation, and a separate query-database connection exist. The query path was not run end to end. |
| 03 — Evaluation harness | PARTIAL / NOT RUN | Runners and golden data exist. The imported case list is only five cases due to a second assignment overriding the earlier list. No fresh baseline report was produced. |
| 04 — Schema RAG | IMPLEMENTED COMPONENTS; EVALUATION REPORTED, NOT REPRODUCED | Curated documents, FTS, OpenAI embeddings, pgvector retrieval, hybrid RRF, and a 15-case benchmark are present. Supplied benchmark figures favor FTS on the current corpus, but no raw report is checked in and results were not reproduced in this audit. Retrieval is not integrated into SQL generation. |
| 05 — MCP integration | NOT STARTED | No MCP integration found. |
| 06 — LangGraph workflow | NOT STARTED | No LangGraph integration found. |
| 07 — Context and token optimization | NOT STARTED | No measurement or implementation found. |
| 08 — Hardening | SCAFFOLDING ONLY | Auth/RBAC, cache, Celery, and telemetry code exists, but integration and operational behavior are not verified. The baseline does not show a complete SQL object allowlist or dedicated read-only DB role. |

The current execution priority is Phase 01, followed by reliable Phase 02/03 verification. Early Phase 04/08 code does not satisfy those phase exit criteria and is not a reason to advance the roadmap.

## Phase 01 — Database and ground truth
**Current status:** PARTIAL / NOT VERIFIED

**Goal:** Reliable synthetic retail data and independently verified expected results.

Work:
- Define and validate schema, relationships, constraints, and business semantics.
- Make database initialization and seeding reproducible.
- Define revenue/order metrics and date semantics.
- Keep reference SQL and expected outputs independent of model output.

Exit criteria:
- Fresh database can be created from documented steps, including schema and seed data.
- Seed process is repeatable and expected counts are checked.
- Constraints and relationships are validated.
- Ground-truth queries return reproducible results.

## Phase 02 — Baseline Text-to-SQL
**Current status:** PROTOTYPE / NOT END-TO-END TESTED

**Goal:** A working baseline without retrieval or agent orchestration.

Work:
- Accept natural-language questions with bounded input.
- Supply bounded schema context.
- Generate structured SQL.
- Validate generated SQL deterministically.
- Execute with restricted credentials and resource limits.
- Return rows, SQL, and controlled errors.

Exit criteria:
- End-to-end baseline works for the supported question set.
- Safety controls are deterministic and tested.
- Failures are captured and understandable.

## Phase 03 — Evaluation harness
**Current status:** PARTIAL / NOT RUN AGAINST A LIVE DATABASE

**Goal:** Measure quality before adding advanced capabilities.

Work:
- Keep a stable, complete set of golden questions and expected results.
- Compare result sets with explicit ordering, duplicate, NULL, numeric, date, and alias rules.
- Track SQL validity, execution, result accuracy, answer correctness, security, latency, and token usage separately.
- Fix the duplicate golden-case assignment and honor per-case ordering/tolerance.

Exit criteria:
- Repeatable evaluation against a reproducibly initialized database.
- Fresh baseline report and regression suite.
- Known failures categorized with actual outputs.

## Phase 04 — Schema RAG
**Current status:** RETRIEVAL COMPONENTS IMPLEMENTED; REPORTED METRICS NOT REPRODUCED; NOT INTEGRATED

**Goal:** Improve relevant schema/business-context retrieval.

Work:
- Maintain the 11 traceable schema/business documents.
- Keep document and embedding indexing repeatable; verify database permissions and migration setup.
- Re-run the 15-case FTS/vector/hybrid comparison and preserve its raw output, configuration, and database state.
- Keep FTS as the preferred baseline only for the current corpus unless a reproducible benchmark changes the trade-off.
- Integrate retrieved context into SQL generation only after Phases 01–03 have reliable exit evidence; evaluate downstream SQL/result accuracy against the same baseline set.

Exit criteria:
- Repeatable document/embedding ingestion and live retrieval integration tests.
- Reproducible retrieval report for all strategies.
- Downstream comparison against the stable baseline showing measured impact before claiming RAG improves query quality.

## Phase 05 — MCP integration
**Current status:** NOT STARTED

Introduce MCP only for a demonstrated interface need. Tools must have narrow contracts, authorization, bounded execution, and integration tests.

## Phase 06 — LangGraph workflow
**Current status:** NOT STARTED

Introduce explicit stateful orchestration only if the workflow requires it. Bound retries, steps, tool calls, time, and state size; compare accuracy with the baseline.

## Phase 07 — Context and token optimization
**Current status:** NOT STARTED

Measure token budgets, latency, and cost before reducing context. Do not trade away accuracy without measured evidence.

## Phase 08 — Hardening
**Current status:** SCAFFOLDING ONLY

Complete and test authentication/authorization, SQL security/resource governance, prompt-injection defenses, observability, regression/load testing, and operational documentation. Existing scaffold code is not phase completion.

## Phase advancement rule

Do not advance solely because code or dependencies have been added. Review exit criteria and record evidence in `PROJECT_STATE.md`.
