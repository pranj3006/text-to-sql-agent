# Evaluation Strategy

**Current status:** Query-generator evaluation remains partially implemented and has not been freshly run against a live database. Schema-retrieval evaluation code now covers FTS, vector, and hybrid retrieval over 15 cases. The benchmark figures below were supplied in the project progress summary; no raw report is checked in and they were not independently reproduced during this documentation audit.

## Current implementation

- `src/text_to_sql_agent/evaluation/golden_cases.py` defines `GOLDEN_CASES` twice. The second assignment replaces the first at import time, so the active cases are Q02, Q03, Q04, Q07, and Q09 (5 cases).
- `run_golden.py` executes reference SQL and writes `golden_results.json`.
- `run_baseline.py` calls the model, executes generated/reference SQL, compares results, and writes `baseline_results.json`.
- Existing JSON result files are historical snapshots; they are not evidence of a current passing run.
- The baseline comparator sorts row signatures for every case even though `ORDER_SENSITIVE_CASES` is declared. Numeric values are compared exactly after normalization; there is no per-case tolerance or duplicate/ordering policy.
- The active retrieval benchmark is `src/text_to_sql_agent/evaluation/rag/retrieval_cases.py`; its test asserts 15 unique cases and that relevance labels reference the 11 curated schema documents.
- `evaluate_fts_retrieval.py`, `evaluate_vector_retrieval.py`, and `evaluate_hybrid_retrieval.py` run the same retrieval cases and report Recall@3/5/10, Precision@5, MRR@10, nDCG@5, and latency. Hybrid retrieval runs FTS and vector search concurrently and fuses the ranked lists with RRF.
- Each retrieval case also defines `retrieval_query`, but the three evaluators currently pass `question` to the retrievers. The benchmark therefore measures the question wording, not the separate `retrieval_query` field.
- The retrieval evaluators print reports but do not save a result artifact. Vector and hybrid evaluation call the configured embedding provider; FTS does not.
- Unit tests cover retrieval metrics, benchmark cases, RRF, and hybrid-retriever behavior. Database access and live embedding-provider behavior are not established by those unit tests. The live FTS retrieval test requires PostgreSQL.

Correct the duplicate query-generator case declaration and comparator behavior before relying on its metrics. Run live retrieval evaluation only after a reproducible database and embeddings are available, and save the exact command and fresh output as a benchmark artifact before treating numbers as verified.

## Schema-retrieval benchmark

The corpus contains 11 curated documents: four table descriptions, three relationships, and four business rules. The benchmark contains 15 cases (R01–R15). Each case assigns relevance grades to documents; reported metrics are macro-averaged across cases. Retrieval is limited to 10 documents, so Recall@10 can be saturated for this small corpus and is less discriminative.

The latest figures in the user-provided progress summary were:

| Metric | FTS | Vector | Hybrid RRF |
|---|---:|---:|---:|
| Recall@3 | 0.644 | 0.622 | 0.622 |
| Recall@5 | 0.833 | 0.755 | 0.833 |
| Recall@10 | 1.000 | 1.000 | 1.000 |
| Precision@5 | 0.720 | 0.667 | 0.720 |
| MRR@10 | 0.956 | 0.967 | 1.000 |
| nDCG@5 | 0.921 | 0.890 | 0.954 |
| Mean latency (ms) | 6.88 | 433.93 | 425.10 |

These are reported results, not a reproducible checked-in report. They support treating FTS as the preferred retrieval baseline for the current corpus: hybrid's reported ranking gains came with substantially higher latency, while vector retrieval did not consistently improve relevance. This is a corpus-specific choice, not a general claim, and no FTS default is wired into the Text-to-SQL query flow.

To reproduce the comparison, prepare the document table, index documents and embeddings, then run each evaluator described in [README.md](../README.md#rag-retrieval-evaluation). Record the database/document state, embedding model, exact command, and complete output. The current evaluators time each individual retrieval once, so the latency figures are sensitive to cold starts, network state, and embedding API latency.

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
