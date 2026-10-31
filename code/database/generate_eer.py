"""Generate an editable EER and SVG from the ACTUAL MySQL schema (no guesses).

Usage:
  python code/database/generate_eer.py --database timaflu_casus_test_94
Uses TIMAFLU_TEST_MYSQL_HOST/PORT/PASSWORD, localhost isolated DB only.
The document is derived from information_schema, not manually guessed entities.
"""
import argparse
import json
import os
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Documentation/Architecture"
GROUPS = [
    ["Adres", "Klant", "PotentieleKlant", "Acquisitiebezoek", "Klantkorting"],
    ["Product", "ProductWerkzameStof", "Magazijnlocatie", "Leverancier",
     "LeveranciersAanbod", "Inkoopbestelling", "Inkoopbestelregel", "Inkoopfactuur"],
    ["Bestelling", "Bestelregel", "OrderStatus", "Voorraadreservering", "Robot",
     "Deelorder", "Deelorderregel", "Verzamelbak"],
    ["Koerier", "Rit", "Levering", "Leverpoging", "Leveringregel"],
    ["Factuur", "Betalingsherinnering"],
]


def collect(connection, schema):
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute("""
            SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_KEY
            FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s
            ORDER BY TABLE_NAME,ORDINAL_POSITION
        """, (schema,))
        columns = cursor.fetchall()
        cursor.execute("""
            SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_NAME,
                   REFERENCED_COLUMN_NAME,CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME,CONSTRAINT_NAME,ORDINAL_POSITION
        """, (schema,))
        keys = cursor.fetchall()
        cursor.execute("""
            SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=%s AND NON_UNIQUE=0 AND INDEX_NAME <> 'PRIMARY'
            ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
        """, (schema,))
        unique_rows = cursor.fetchall()
    tables = {}
    for col in columns:
        name = col["TABLE_NAME"]
        tables.setdefault(name, []).append({
            "name": col["COLUMN_NAME"], "type": col["COLUMN_TYPE"],
            "nullable": col["IS_NULLABLE"] == "YES", "key": col["COLUMN_KEY"]
        })
    links = [dict(table=k["TABLE_NAME"], column=k["COLUMN_NAME"],
                  target=k["REFERENCED_TABLE_NAME"],
                  target_column=k["REFERENCED_COLUMN_NAME"],
                  constraint=k["CONSTRAINT_NAME"]) for k in keys]
    uniques = {}
    for index in unique_rows:
        table_uniques = uniques.setdefault(index["TABLE_NAME"], {})
        table_uniques.setdefault(index["INDEX_NAME"], []).append(index["COLUMN_NAME"])
    return tables, links, uniques


def layout(tables, uniques):
    positions = {}
    represented = set()
    for column, group in enumerate(GROUPS):
        y = 45
        for name in group:
            if name not in tables:
                continue
            height = 49 + 20 * (len(tables[name]) + len(uniques.get(name, {})))
            positions[name] = (40 + column * 385, y, 343, height)
            represented.add(name)
            y += height + 47
    unknown = set(tables) - represented
    if unknown:
        raise ValueError(f"Unclassified tables in schema: {sorted(unknown)}")
    return positions


def drawio(tables, links, uniques, positions):
    mxfile = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17")
    diagram = ET.SubElement(mxfile, "diagram", id="schema-case-94", name="EER vanuit werkende MySQL")
    model = ET.SubElement(diagram, "mxGraphModel", dx="1400", dy="900", grid="1",
                          gridSize="10", guides="1", tooltips="1",
                          connect="1", arrows="1", fold="1", page="1",
                          pageScale="1", pageWidth="2200", pageHeight="5500")
    graph = ET.SubElement(model, "root")
    ET.SubElement(graph, "mxCell", id="0")
    ET.SubElement(graph, "mxCell", id="1", parent="0")
    for name, (x, y, width, height) in positions.items():
        description = name + "\n" + "\n".join(
            ("PK " if col["key"] == "PRI" else
             "FK " if any(link["table"] == name and link["column"] == col["name"] for link in links) else
             "   ") + col["name"] + " : " + col["type"]
            for col in tables[name]
        )
        if uniques.get(name):
            description += "\n" + "\n".join(
                "UQ " + idx + " (" + ", ".join(fields) + ")"
                for idx, fields in uniques[name].items()
            )
        cell = ET.SubElement(graph, "mxCell", id="entity_" + name, value=description,
                             style="rounded=1;whiteSpace=wrap;html=0;align=left;"
                                   "verticalAlign=top;spacing=9;fontSize=12;"
                                   "fillColor=#FFFFFF;strokeColor=#35465F;",
                             vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y),
                      width=str(width), height=str(height), **{"as":"geometry"})
    for n, link in enumerate(links):
        edge = ET.SubElement(graph, "mxCell", id="foreign_key_"+str(n),
                             value=link["column"], edge="1", parent="1",
                             source="entity_"+link["table"], target="entity_"+link["target"],
                             style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;"
                                   "strokeColor=#8A97A8;fontSize=9;endArrow=open;")
        ET.SubElement(edge, "mxGeometry", relative="1", **{"as":"geometry"})
    return ET.tostring(mxfile, encoding="utf-8", xml_declaration=True)


def svg(tables, links, uniques, positions):
    width = 5 * 385 + 55
    height = max(y + h + 55 for x, y, w, h in positions.values())
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke="#A0ACBD"/></marker></defs>',
    ]
    for edge in links:
        x, y, w, h = positions[edge["table"]]
        tx, ty, tw, th = positions[edge["target"]]
        a, b, c, d = x+w/2, y+h/2, tx+tw/2, ty+th/2
        lines.append(f'<path d="M{a:.0f},{b:.0f} L{c:.0f},{d:.0f}" stroke="#D0D6DF" stroke-width="1.2" fill="none" marker-end="url(#arrow)"/>')
    for name, (x,y,w,h) in positions.items():
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="white" stroke="#35465F" stroke-width="1.4"/>')
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="29" rx="6" fill="#E8EEF8" />')
        lines.append(f'<text x="{x+10}" y="{y+20}" font-family="Arial" font-size="14" font-weight="bold" fill="#21314A">{escape(name)}</text>')
        for n, col in enumerate(tables[name]):
            pk = "PK " if col["key"] == "PRI" else ""
            fk = "FK " if any(link["table"]==name and link["column"]==col["name"] for link in links) else ""
            label = f'{pk}{fk}{col["name"]} : {col["type"]}'
            lines.append(f'<text x="{x+10}" y="{y+49+n*20}" font-family="monospace" font-size="11" fill="#263548">{escape(label)}</text>')
        for n,(idx,fields) in enumerate(uniques.get(name, {}).items()):
            label = "UQ " + idx + ": " + ",".join(fields)
            at = y + 49 + 20*(len(tables[name])+n)
            lines.append(f'<text x="{x+10}" y="{at}" font-family="monospace" font-size="10" fill="#5A3A72">{escape(label)}</text>')
    lines.append('</svg>')
    return ("\n".join(lines)+"\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if os.getenv("TIMAFLU_TEST_ALLOW_RESET") != "isolated" or os.getenv("TIMAFLU_TEST_MYSQL_HOST") != "127.0.0.1":
        raise SystemExit("Only an explicitly isolated localhost DB may be used")
    cnx = mysql.connector.connect(
        host="127.0.0.1", port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        user=os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
        password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        database=args.database,
    )
    try:
        tables, links, uniques = collect(cnx, args.database)
    finally:
        cnx.close()
    positions = layout(tables, uniques)
    outputs = {
        "eer-mysql-verified.drawio": drawio(tables,links,uniques,positions),
        "eer-mysql-verified.svg": svg(tables,links,uniques,positions),
        "eer-mysql-schema.json": (json.dumps(
            {"tables":tables,"foreign_keys":links,"unique_keys":uniques}, ensure_ascii=False,indent=2
        )+"\n").encode("utf-8"),
    }
    for name, data in outputs.items():
        target=OUT / name
        if args.check:
            if not target.exists() or target.read_bytes()!=data:
                raise SystemExit(f"EER is out of sync: {name}")
        else:
            target.write_bytes(data)
    print(f"EER {'verified' if args.check else 'generated'}: {len(tables)} tables, {len(links)} foreign-key columns")


if __name__ == "__main__":
    main()
