
import json
import time
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text

from text_to_sql_agent.app.text_to_sql import engine, generate_sql, validate_sql
from text_to_sql_agent.evaluation.query_generator.golden_cases import GOLDEN_CASES

OUTPUT_FILE = Path(__file__).with_name("baseline_results.json")

# These cases require the result ranking/order to be preserved.
ORDER_SENSITIVE_CASES = {"Q02", "Q08", "Q10"}


def normalize(value):
    if value is None:
        return ("null", None)

    if isinstance(value, bool):
        return ("boolean", value)

    if isinstance(value, (int, float, Decimal)):
        return ("number", Decimal(str(value)).normalize())

    if isinstance(value, datetime):
        # PostgreSQL DATE_TRUNC('month', ...) produces midnight
        # on the first day of a month. Normalize that to a date.
        if value.time().isoformat() == "00:00:00":
            return ("date", value.date().isoformat())
        return ("datetime", value.isoformat())

    if isinstance(value, date):
        return ("date", value.isoformat())

    return ("string", str(value))


def compare_results(expected_rows, actual_rows,expected_columns=None):
    """
    Compare expected business columns by name.
    Extra generated columns are reported separately.
    """    
    if expected_columns is None:
        
        if expected_rows:
            expected_columns = (
                list(expected_rows[0].keys()) if expected_rows else []
            )        
    if len(expected_rows)==0:
        expected_columns = []
        
    actual_columns = (
        list(actual_rows[0].keys()) if actual_rows else []
    )

    missing_columns = [
        col for col in expected_columns if col not in actual_columns
    ]
    extra_columns = [
        col for col in actual_columns if col not in expected_columns
    ]

    if missing_columns:
        return {
            "result_match": False,
            "output_schema_match": False,
            "expected_columns": expected_columns,
            "actual_columns": actual_columns,
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
            "expected_rows": expected_rows,
            "actual_rows": actual_rows,
        }

    def signatures(rows):
        return sorted(
            tuple(
                (col, normalize(row[col]))
                for col in expected_columns
            )
            for row in rows
        )

    result_match = signatures(expected_rows) == signatures(actual_rows)

    return {
        "result_match": result_match,
        "output_schema_match": not extra_columns,
        "expected_columns": expected_columns,
        "actual_columns": actual_columns,
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "expected_rows": expected_rows,
        "actual_rows": actual_rows,
    }


def fetch_rows(sql):
    """Execute a query in a read-only transaction with a timeout."""
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(
                text("SET LOCAL statement_timeout = '5000ms'")
            )
            result = connection.execute(text(sql))
            return [dict(row) for row in result.mappings()]


def main():
    report = []

    for case in GOLDEN_CASES:
        case_id = case["id"]
        started = time.perf_counter()
        expected_columns = case.get("expected_columns",[])
        entry = {
            "id": case_id,
            "question": case["question"],
            "status": "ERROR",
            "expected_columns":expected_columns
        }

        try:
            generated_sql = generate_sql(case["question"])
            safe_sql = validate_sql(generated_sql)

            actual_rows = fetch_rows(safe_sql)
            expected_rows = fetch_rows(case["reference_sql"])

            # actual_signatures = [
            #     row_signature(row) for row in actual_rows
            # ]
            # expected_signatures = [
            #     row_signature(row) for row in expected_rows
            # ]

            # if case_id in ORDER_SENSITIVE_CASES:
            #     actual_comparable = actual_signatures
            #     expected_comparable = expected_signatures
            # else:
            #     actual_comparable = sorted(actual_signatures)
            #     expected_comparable = sorted(expected_signatures)

            comparison = compare_results(expected_rows, actual_rows,expected_columns)

            entry.update(comparison)
            entry["status"] = (
                "PASS"
                if comparison["result_match"]
                and comparison["output_schema_match"]
                else "PASS_WITH_SCHEMA_MISMATCH"
                if comparison["result_match"]
                else "FAIL"
            )
            entry["generated_sql"] = safe_sql
            
            # passed = actual_comparable == expected_comparable

            # entry.update({                
            #     "generated_sql": safe_sql,
            #     "expected_row_count": len(expected_rows),
            #     "actual_row_count": len(actual_rows),
            #     "expected_rows": expected_rows,
            #     "actual_rows": actual_rows,
            # })

        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"

        entry["latency_seconds"] = round(
            time.perf_counter() - started, 3
        )
        report.append(entry)

        print(
            f"{entry['status']:5} {case_id} "
            f"({entry['latency_seconds']}s) "
            f"{case['question']}"
        )

        if "error" in entry:
            print(f"      Error: {entry['error']}")

    passed = sum(item["status"] == "PASS" for item in report)
    failed = sum(item["status"] == "FAIL" for item in report)
    errors = sum(item["status"] == "ERROR" for item in report)

    summary = {
        "total": len(report),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy": round(passed / len(report), 4) if report else 0,
        "results": report,
    }

    OUTPUT_FILE.write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    print("\n--- Baseline evaluation summary ---")
    print(f"Total:    {len(report)}")
    print(f"Passed:   {passed}")
    print(f"Failed:   {failed}")
    print(f"Errors:   {errors}")
    print(f"Accuracy: {summary['accuracy']:.1%}")
    print(f"Report:   {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
