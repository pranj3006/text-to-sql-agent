import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from text_to_sql_agent.evaluation.golden_cases import GOLDEN_CASES
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

OUTPUT_FILE = Path(__file__).with_name("golden_results.json")


def json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def main():
    results = []

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        for case in GOLDEN_CASES:
            with conn.cursor() as cur:
                cur.execute(case["reference_sql"])
                rows = cur.fetchall()

            result = {
                "id": case["id"],
                "question": case["question"],
                "columns": list(rows[0].keys()) if rows else [],
                "rows": [dict(row) for row in rows],
            }
            results.append(result)

            print(f"\n[{case['id']}] {case['question']}")
            print(json.dumps(result["rows"], default=json_default, indent=2))

    OUTPUT_FILE.write_text(
        json.dumps(results, default=json_default, indent=2),
        encoding="utf-8",
    )

    print(f"\nExecuted {len(results)} golden cases.")
    print(f"Saved expected results to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()