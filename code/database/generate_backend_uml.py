"""Generate the definitive class index/PlantUML/SVG from actual Python classes."""
import argparse
import ast
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "code/backend"
OUT = ROOT / "Documentation/Architecture"
SECTIONS = ["domain", "repositories", "services"]


def collect():
    classes = []
    for section in SECTIONS:
        for file in sorted((BACKEND / section).glob("*.py")):
            if file.name.startswith("test_"):
                continue
            module = f"{section}.{file.stem}"
            source = ast.parse(file.read_text(encoding="utf-8"))
            for klass in source.body:
                if not isinstance(klass, ast.ClassDef):
                    continue
                methods = [node.name for node in klass.body if isinstance(node, ast.FunctionDef)]
                classes.append({"module": module, "class": klass.name,
                                "methods": methods})
    return classes


def plantuml(classes):
    out = ["@startuml Timaflu_backend_live", "title Backendklassendiagram uit Python-broncode",
           "hide empty members", "skinparam linetype ortho", "left to right direction"]
    ids = {}
    for section in SECTIONS:
        out.append(f'package "{section}" {{')
        for index, klass in enumerate(classes):
            if not klass["module"].startswith(section+"."):
                continue
            alias = "C" + str(index)
            ids[(klass["module"], klass["class"])] = alias
            out.append(f'  class "{klass["module"]}.{klass["class"]}" as {alias} {{')
            for method in klass["methods"]:
                out.append(f"    +{method}()")
            out.append("  }")
        out.append("}")
    for a,b in [
        (("repositories.weekly_invoice_repository","WeeklyInvoiceRepository"),
         ("domain.business","Invoice")),
        (("repositories.weekly_invoice_repository","WeeklyInvoiceRepository"),
         ("repositories.assessed_repository","AssessedRepository")),
        (("domain.business","Invoice"),("domain.business","Order")),
    ]:
        if a in ids and b in ids:
            out.append(f'{ids[a]} ..> {ids[b]} : gebruikt')
    out.append("@enduml")
    return ("\n".join(out)+"\n").encode("utf-8")


def svg(classes):
    cols = 4
    width = 4 * 440 + 45
    positions = {}
    y_by_col = [54] * cols
    for index,klass in enumerate(classes):
        col = index % cols
        h = 46 + 18 * max(1,len(klass["methods"]))
        x = 20 + col * 440
        y = y_by_col[col]
        positions[index] = (x, y, h)
        y_by_col[col] += h + 32
    height = max(y_by_col) + 15
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>'
    ]
    for index,klass in enumerate(classes):
        x,y,h = positions[index]
        title = klass["module"]+"."+klass["class"]
        lines.extend([
            f'<rect x="{x}" y="{y}" width="416" height="{h}" rx="5" stroke="#42536C" fill="#fff"/>',
            f'<rect x="{x}" y="{y}" width="416" height="28" rx="5" fill="#E7EDF5"/>',
            f'<text x="{x+8}" y="{y+19}" font-family="Arial" font-size="12" font-weight="bold">{escape(title)}</text>'
        ])
        for n, method in enumerate(klass["methods"]):
            lines.append(f'<text x="{x+10}" y="{y+46+n*18}" font-family="monospace" font-size="11">{escape(method)}()</text>')
    lines.append("</svg>")
    return ("\n".join(lines)+"\n").encode("utf-8")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    classes=collect()
    artifacts={
        "class-diagram-backend.puml":plantuml(classes),
        "class-diagram-backend.svg":svg(classes),
        "class-index.json":(json.dumps(classes,ensure_ascii=False,indent=2)+"\n").encode("utf-8"),
    }
    for name, contents in artifacts.items():
        path=OUT/name
        if args.check:
            if not path.exists() or path.read_bytes()!=contents:
                raise SystemExit(f"Backend UML outdated: {name}")
        else:
            path.write_bytes(contents)
    print(f"Backend UML {'checked' if args.check else 'generated'}: {len(classes)} real classes")


if __name__=="__main__":
    main()
