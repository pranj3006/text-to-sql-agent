# Evaluation Strategy

**Current status:** The evaluation code and reference SQL exist, but no fresh model-backed or database-backed evaluation was run during the 2026-11-06 audit.

## Current implementation

- `src/text_to_sql_agent/evaluation/golden_cases.py` defines `GOLDEN_CASES` twice. The second assignment replaces the first at import time, so the active cases are Q02, Q03, Q04, Q07, and Q09 (5 cases).
- `run_golden.py` executes reference SQL and writes `golden_results.json`.
- `run_baseline.py` calls the model, executes generated/reference SQL, compares results, and writes `baseline_results.json`.
- Existing JSON result files are historical snapshots; they are not evidence of a current passing run.
- The baseline comparator sorts row signatures for every case even though `ORDER_SENSITIVE_CASES` is declared. Numeric values are compared exactly after normalization; there is no per-case tolerance or duplicate/ordering policy.
- Current automated tests cover schema-document construction only, not the evaluation runners or database/model boundaries.

Correct the duplicated case declaration and comparator behavior before relying on evaluation metrics. Run the evaluation only after a reproducible database is available, and preserve the exact command and fresh output in project state.

## Principles

- SQL syntax validity is not semantic correctness.
- SQL string equality is usually too strict because equivalent queries can differ syntactically.
- Expected results must come from independently verified ground truth.
- Do not leak hidden expected aliases or expected result structure into the SQL-generation prompt merely to game evaluation.
- Report separate dimensions rather than collapsing everything into one PASS/FAIL.

## Evaluation dimensions

| Dimension | What it measures |
|---|---|
| Generation validity | Structured output and SQL parse success |
| Schema validity | Referenced objects/columns exist and are permitted |
| Execution success | Query executes under restricted credentials |
| Result accuracy | Actual result matches expected result |
| Answer correctness | Natural-language answer faithfully describes rows |
| Grounding | Claims are supported by returned data |
| Security | Unsafe or unauthorized queries are rejected |
| Efficiency | Tokens, latency, database time, and model cost |

## Result comparison policy

Define comparison rules per question:
- Is row ordering significant?
- Are duplicates significant?
- How are NULLs compared?
- What numeric tolerance is acceptable?
- Are date/time boundaries inclusive or exclusive?
- Are aliases part of the external response contract, or presentation metadata?
- Are additional columns allowed or a contract mismatch?

A useful evaluator reports semantic result accuracy and output-contract/schema mismatch separately. Keep expected outputs independent of model generations.

## Historical issues

Earlier documentation mentioned alias mismatches and temporarily skipped cases, but those reports were not reproduced in this audit and are not current evaluation results. The active imported case list does not include Q06 or Q08. Re-run and record any outcomes against the current code; do not make the generator aware of hidden expected aliases merely to pass evaluation.
