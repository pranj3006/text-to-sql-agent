# Architecture — Agentic Text-to-SQL

## 1. Target outcome

A user submits a natural-language analytics question. The system retrieves relevant schema/business context, generates SQL, applies deterministic safety validation, executes with restricted database access, verifies whether the result answers the question, and returns the answer with SQL and supporting evidence.

## 2. Target logical flow

```mermaid
flowchart TD
    A[User question] --> B[FastAPI]
    B --> C[Application workflow]
    C --> D[Intent and metric understanding]
    D --> E[Schema/business context]
    E --> F[SQL generation]
    F --> G[Deterministic SQL validation]
    G -->|Rejected| H[Safe error / bounded correction]
    G -->|Accepted| I[Read-only SQL execution]
    I --> J[Result inspection and verification]
    J --> K[Grounded answer + SQL + evidence + metadata]
```

The baseline should implement the smallest useful deterministic subset of this flow. Retrieval, MCP, and LangGraph are introduced only when their roadmap entry criteria are met. Current code has an experimental full-text retrieval path that is not yet a complete or verified RAG flow.

## 3. Component responsibilities

### API
- Accept and validate requests.
- Apply authentication/authorization boundaries as the application evolves.
- Invoke application use cases and return stable response contracts.

### Application/workflow
- Coordinate question processing and execution budgets.
- Keep orchestration independent of provider-specific details.

### Schema knowledge
- Store traceable table/column descriptions, relationships, business terms, and metric definitions.
- Supply only relevant context to generation; retrieval quality must be measured.

### SQL generation
- Translate user intent and supplied context into SQL.
- Identify ambiguity rather than inventing business meaning.
- Keep provider integration replaceable.

### SQL validation/security
- Parse and inspect SQL deterministically.
- Enforce one statement, read-only operations, allowlisted objects, safe functions, and query constraints.
- Never rely solely on an LLM prompt.

### Execution
- Use a dedicated read-only database role.
- Enforce statement timeout and result row limits.
- Return controlled result metadata and sanitized errors.

### Verification and response
- Compare results and response claims against evidence.
- Ground natural-language claims in returned rows and metadata.
- Return SQL and evidence for inspection.

### MCP and LangGraph (later)
MCP may expose narrowly scoped capabilities with validated contracts and authorization. LangGraph may coordinate stateful execution and bounded recovery. Neither replaces deterministic validation or authorization.

## 4. Trust boundaries

Treat user questions, retrieved schema descriptions/business text, database content, model-generated SQL/explanations, and tool outputs as untrusted. Only deterministic application/database controls enforce permissions and execution policy.

## 5. Non-functional requirements

- Correctness and traceability
- Least privilege
- Bounded latency, tokens, retries, and query resources
- Testability and reproducibility
- Provider replaceability
- Clear failure modes
- Observable execution without leaking sensitive data

## 6. Observed implementation (2026-11-06)

- `app/main.py` defines a FastAPI `/health` endpoint and synchronous `/query` handler.
- `app/text_to_sql.py` contains a separate synchronous SQLAlchemy engine, static schema/business context, OpenAI SQL generation, SQLGlot parsing, a SELECT/set-operation gate, a blocked-function list, a default row cap, a read-only transaction, and a statement timeout.
- The current validator does not enforce an allowlist of schemas/tables/columns. The checked-in Docker initialization creates a regular database user with database-wide privileges; it does not define a dedicated read-only role.
- `app/rag/` contains curated schema documents, a PostgreSQL `tsvector` schema, and full-text retrieval. It does not contain embedding generation or vector retrieval.
- Several supporting modules still use imports from the former `app.*` package, while the repository is now under `text_to_sql_agent.*`. The schema-indexing script also calls an async indexer without awaiting it.
- The app scaffold uses an async engine and centralized settings, while the baseline query path independently reads environment variables and creates a sync engine. These paths have not been integrated or exercised end to end.
- Auth/RBAC, Celery, cache, and telemetry modules are scaffolding; their production behavior is not established by the current tests.
- No MCP or LangGraph workflow is present.

This section records code presence and observed wiring only; it is not a security review or runtime verification. See `PROJECT_STATE.md` for test results and `ROADMAP.md` for phase status. `DECISIONS.md` records accepted choices.
