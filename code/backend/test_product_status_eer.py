"""Timaflu has distinct sales assortment and internal reorder-list flags."""
from pathlib import Path
from unittest import TestCase
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]


class ProductStatusEERTests(TestCase):
    def test_two_case_states_are_distinct_and_in_eer(self):
        schema=(ROOT/"code/database/schema.sql").read_text(encoding="utf-8")
        self.assertIn("intern_bestelbaar BOOLEAN NOT NULL DEFAULT TRUE",schema)
        self.assertIn("in_assortiment BOOLEAN NOT NULL DEFAULT TRUE",schema)
        with zipfile.ZipFile(ROOT/"eer.mwb") as wb:
            self.assertIsNone(wb.testzip())
            tree=ET.fromstring(wb.read("document.mwb.xml"))
        tables=[t for t in tree.iter("value") if t.get("struct-name")=="db.mysql.Table"]
        product=next(t for t in tables if
                     t.find("./value[@key='name']").text=="product")
        columns={c.find("./value[@key='name']").text for c in product.iter("value")
                 if c.get("struct-name")=="db.mysql.Column"}
        self.assertIn("in_assortiment",columns)
        self.assertIn("intern_bestelbaar",columns)
        reorder_sql=(ROOT/"code/database/queries.sql").read_text(encoding="utf-8")
        self.assertIn("intern_bestelbaar = TRUE AND p.in_assortiment = TRUE",reorder_sql)
