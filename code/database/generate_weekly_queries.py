"""Rebuild exact weekly-invoice screen SQL examples from repository statements.

Usage: python code/database/generate_weekly_queries.py [--check]
Ensures the repository and code/database/queries.sql cannot silently diverge.
"""
import argparse
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "backend" / "repositories" / "weekly_invoice_repository.py"
TARGET = HERE / "queries.sql"
BEGIN = "-- BEGIN GENERATED WEEKLY INVOICE QUERIES"
END = "-- END GENERATED WEEKLY INVOICE QUERIES"
EXAMPLES = {
    ("eligible_customers", 0): ["'2026-10-19'", "'2026-10-25'"],
    ("_issue_customer", 0): ["1"],
    ("_issue_customer", 1): ["1", "'2026-10-19'"],
    ("_issue_customer", 2): ["1", "'2026-10-19'", "'2026-10-25'"],
    ("_issue_customer", 3): ["1", "'2025-01-01'", "'2026-01-01'"],
    ("_issue_customer", 4): ["1"],
    ("_issue_customer", 5): [
        "1", "'2026-10-31'", "'2026-10-19'",
        "'Voorbeeldadres alleen voor test'", "'Testapotheekstraat 1'"
    ],
    ("_issue_customer", 6): ["2", "2", "1"],
    ("_issue_customer", 7): ["2"],
    ("issued_invoice", 0): ["2"],
    ("issued_invoice", 1): ["2"],
}


def extract():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    seen = []
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for method in cls.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            calls = sorted(
                (n for n in ast.walk(method) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "execute"),
                key=lambda n: n.lineno
            )
            for index, call in enumerate(calls):
                sql = ast.literal_eval(call.args[0]).strip()
                key = (method.name, index)
                values = EXAMPLES[key]
                assert sql.count("%s") == len(values), (key, sql)
                for value in values:
                    sql = sql.replace("%s", value, 1)
                seen.append(f"-- WeeklyInvoiceRepository.{method.name} example {index + 1}\n{sql};")
    assert len(seen) == len(EXAMPLES), (len(seen), len(EXAMPLES))
    return BEGIN + "\n" + "\n\n".join(seen) + "\n" + END


def run(check=False):
    original = TARGET.read_text(encoding="utf-8")
    rendered = extract()
    if BEGIN in original:
        previous = original.split(BEGIN, 1)[1].split(END, 1)[0]
        existing = BEGIN + previous + END
        updated = original.replace(existing, rendered)
    else:
        updated = original.rstrip() + "\n\n" + rendered + "\n"
    if check:
        if updated != original:
            raise SystemExit("Weekly repository SQL is out of sync with queries.sql")
        print("Weekly SQL mirrored: OK")
    else:
        TARGET.write_text(updated, encoding="utf-8")
        print("Generated weekly invoice statements in queries.sql")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    run(parser.parse_args().check)
