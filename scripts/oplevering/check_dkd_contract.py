"""Check that the original Timaflu domain class diagram matches Python code.

Unlike the generated backend class diagram, this verification uses the approved
DKD as an independent source. No database, credentials or fixtures are needed.
Run: python scripts/oplevering/check_dkd_contract.py
"""
from __future__ import annotations

import ast
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DKD = ROOT / "Documentation/Architecture/uml/src/domain/dkd-timaflu.puml"
DOMAIN = ROOT / "code/backend/domain"


def diagram_classes():
    text = DKD.read_text(encoding="utf-8")
    result = {}
    for match in re.finditer(r"^class\s+(\w+)\s*\{(.*?)^\}", text, re.M | re.S):
        name, body = match.groups()
        if name in result:
            raise AssertionError(f"Duplicate class in DKD: {name}")
        result[name] = {
            method: len([argument for argument in args.split(",") if argument.strip()])
            for method, args in re.findall(r"^\s*(\w+)\(([^)]*)\)", body, re.M)
        }
    return result


def source_classes():
    result = defaultdict(list)
    for path in sorted(DOMAIN.glob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8"), filename=str(path)).body:
            if isinstance(node, ast.ClassDef):
                result[node.name].append((path.relative_to(ROOT), node))
    return result


def check():
    expected = diagram_classes()
    found = source_classes()
    if len(expected) != 29:
        raise AssertionError(f"Expected 29 original DKD classes; got {len(expected)}")
    issues = []
    for name, methods in expected.items():
        occurrences = found.get(name, ())
        if len(occurrences) != 1:
            issues.append(f"{name}: expected exactly 1 definition, found {len(occurrences)}")
            continue
        path, klass = occurrences[0]
        actual = {
            node.name: node
            for node in klass.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for method, required_parameters in methods.items():
            if method not in actual:
                issues.append(f"{path}: missing {name}.{method}()")
                continue
            node = actual[method]
            parameters = len(node.args.posonlyargs) + len(node.args.args) - 1
            if parameters < required_parameters:
                issues.append(
                    f"{path}: {name}.{method}() expects at least "
                    f"{required_parameters} DKD parameters; got {parameters}"
                )
    if issues:
        raise AssertionError("\n".join(issues))

    # One concrete invariant of the newly added method. Selling a medicine
    # must remain possible when it is excluded from the internal reorder list.
    sys.path.insert(0, str(ROOT / "code/backend"))
    from domain.product import Product
    product = Product(
        product_id=1, article_number="A-1", order_code="B-1",
        product_name="Testmedicijn", price_per_bulk_package=Decimal("20"),
        package_type="doos", number_of_retail_packages=1,
        short_description="", long_description="",
        minimum_order_quantity=1, minimum_stock=5,
    )
    assert product.in_assortment and product.internal_reorder_eligible
    product.removeFromInternalReorderList()
    assert product.in_assortment and not product.internal_reorder_eligible
    print(f"PASS: {len(expected)} unique DKD domain classes, their methods, "
          "minimum signatures and independent reorder-state invariant")


if __name__ == "__main__":
    check()
