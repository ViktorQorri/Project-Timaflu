"""Validate that the editable Workbench EER matches the SQL schema and purchasing code.

Run with: python scripts/oplevering/validate_eer_schema.py
No database connection is required; this inspection is read-only.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
DATATYPES = {
    "int": "int", "varchar": "varchar", "datetime": "datetime_f",
    "date": "date", "decimal": "decimal", "tinyint": "tinyint",
    "bigint": "bigint", "time": "time_f", "text": "text",
    "boolean": "tinyint", "bool": "tinyint", "timestamp": "timestamp",
    "enum": "enum", "char": "char", "year": "year",
    "smallint": "smallint", "float": "float", "double": "double",
    "json": "json", "mediumint": "mediumint",
}


def split_definitions(body: str) -> list[str]:
    """Split CREATE TABLE definitions, ignoring commas in types and strings."""
    body = re.sub(r"(?m)^\s*--[^\n]*$", "", body)
    parts, current, depth, quoted = [], [], 0, False
    for ch in body:
        if ch == "'":
            quoted = not quoted
        elif not quoted and ch == "(":
            depth += 1
        elif not quoted and ch == ")":
            depth -= 1
        if ch == "," and depth == 0 and not quoted:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return parts


def sql_columns() -> dict[str, dict[str, dict]]:
    schema = (ROOT / "code/database/schema.sql").read_text(encoding="utf-8")
    tables = {}
    pattern = r"CREATE\s+TABLE\s+`?([\w]+)`?\s*\((.*?)\)\s*;"
    for table_match in re.finditer(pattern, schema, re.I | re.S):
        columns = {}
        for definition in split_definitions(table_match.group(2)):
            m = re.match(r"^`?([A-Za-z_][\w]*)`?\s+([A-Za-z]+)(?:\s*\(([^)]*)\))?(.*)$",
                         definition, re.I | re.S)
            if not m or m.group(2).lower() not in DATATYPES:
                continue
            name, dtype, detail, rest = m.groups()
            declared_not_null = bool(re.search(r"\bNOT\s+NULL\b|\bPRIMARY\s+KEY\b",
                                               rest, re.I))
            columns[name.lower()] = {
                "type": DATATYPES[dtype.lower()],
                "length": int(detail) if dtype.lower() in {"varchar", "char"} else None,
                "nullable": not declared_not_null,
            }
        tables[table_match.group(1).lower()] = columns
    if not tables:
        raise ValueError("No CREATE TABLE definitions found in schema.sql")
    return tables


def workbench_columns() -> dict[str, dict[str, dict]]:
    with ZipFile(ROOT / "eer.mwb") as archive:
        damaged = archive.testzip()
        if damaged:
            raise ValueError(f"Damaged Workbench archive member: {damaged}")
        root = ET.fromstring(archive.read("document.mwb.xml"))
    ids = [n.attrib["id"] for n in root.iter() if "id" in n.attrib]
    pointers = [n.attrib["_ptr_"] for n in root.iter() if "_ptr_" in n.attrib]
    for values, label in ((ids, "object IDs"), (pointers, "list pointers")):
        duplicates = [key for key, count in Counter(values).items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate Workbench {label}: {duplicates[:5]}")
    tables = {}
    for table in root.iter("value"):
        if table.get("struct-name") != "db.mysql.Table":
            continue
        name_node = table.find("./value[@key='name']")
        if name_node is None or not name_node.text:
            continue
        columns = {}
        for column in table.find("./value[@key='columns']"):
            if column.get("struct-name") != "db.mysql.Column":
                continue
            label = column.find("./value[@key='name']").text
            typename = column.find("./link[@key='simpleType']").text
            length = column.find("./value[@key='length']").text
            columns[label.lower()] = {
                "type": typename.rsplit(".", 1)[-1],
                "length": int(length or "-1"),
                "nullable": column.find("./value[@key='isNotNull']").text != "1",
            }
        tables[name_node.text.lower()] = columns
    return tables


def normalized(value: str) -> str:
    return " ".join(value.lower().split())


def check_purchase_queries() -> None:
    """Reject SQL examples that disagree with actual purchasing repository SQL."""
    repo = (ROOT / "code/backend/repositories/purchase_order_repository.py").read_text(
        encoding="utf-8"
    )
    documented = normalized((ROOT / "code/database/queries.sql").read_text(
        encoding="utf-8"
    ))
    module = ast.parse(repo)
    sql_literals = [
        node.args[0].value for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute" and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]
    lookup = next((q for q in sql_literals if "FROM LeveranciersAanbod AS a" in q),
                  None)
    insert = next((q for q in sql_literals if "INSERT INTO Inkoopbestelling" in q),
                  None)
    if not lookup or not insert:
        raise ValueError("Supplier validation or purchase INSERT missing from repository")
    for query in (lookup, insert):
        example = normalized(query).replace("%s", "1")
        if example not in documented:
            raise ValueError(f"queries.sql differs from repository: {example}")
    recorded = re.search(
        r"SELECT\s+i\.inkoopbestelling_id.*?ORDER\s+BY\s+"
        r"i\.besteld_op\s+DESC,\s*i\.inkoopbestelling_id\s+DESC,\s*p\.productnaam",
        repo, re.I | re.S
    )
    if not recorded or normalized(recorded.group(0)) not in documented:
        raise ValueError("Recorded supplier-order SELECT differs from queries.sql")
    template = (ROOT / "code/frontend/templates/reorder.html").read_text(
        encoding="utf-8"
    )
    if not all(f"item.{name}" in template for name in ("besteld_op", "status_naam")):
        raise ValueError("Reorder screen does not display saved date and status")


def validate() -> None:
    sql = sql_columns()
    eer = workbench_columns()
    problems = []
    if sql.keys() != eer.keys():
        problems.append(f"Table mismatch: SQL-only={sorted(sql.keys()-eer.keys())}; "
                        f"EER-only={sorted(eer.keys()-sql.keys())}")
    for table in sorted(sql.keys() & eer.keys()):
        s, e = sql[table], eer[table]
        if s.keys() != e.keys():
            problems.append(f"{table}: SQL-only={sorted(s.keys()-e.keys())}; "
                            f"EER-only={sorted(e.keys()-s.keys())}")
        for name in sorted(s.keys() & e.keys()):
            for key in ("type", "nullable"):
                if s[name][key] != e[name][key]:
                    problems.append(f"{table}.{name} {key}: SQL={s[name][key]} "
                                    f"EER={e[name][key]}")
            if s[name]["length"] is not None and s[name]["length"] != e[name]["length"]:
                problems.append(f"{table}.{name} length: SQL={s[name]['length']} "
                                f"EER={e[name]['length']}")
    check_purchase_queries()
    if problems:
        raise ValueError("EER / SQL mismatch:\n" + "\n".join(problems))
    print(f"PASS: {len(sql)} SQL tables match eer.mwb; purchasing queries and UI agree")


if __name__ == "__main__":
    validate()
