"""Ensure the editable Workbench EER matches the product assortment schema."""

from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET


REPOSITORY = Path(__file__).resolve().parents[2]


class ProductEERTests(unittest.TestCase):
    def test_product_assortment_column_matches_workbench_model(self):
        with zipfile.ZipFile(REPOSITORY / "eer.mwb") as workbook:
            self.assertIsNone(workbook.testzip())
            root = ET.fromstring(workbook.read("document.mwb.xml"))
        tables = [v for v in root.iter("value")
                  if v.attrib.get("struct-name") == "db.mysql.Table"]
        product = next(v for v in tables
                       if v.find("./value[@key='name']").text == "product")
        columns = [v for v in product.iter("value")
                   if v.attrib.get("struct-name") == "db.mysql.Column"]
        names = [v.find("./value[@key='name']").text for v in columns]
        self.assertEqual(names.count("in_assortiment"), 1)
        assortment = next(c for c in columns
                          if c.find("./value[@key='name']").text == "in_assortiment")
        self.assertEqual(
            assortment.find("./link[@key='simpleType']").text,
            "com.mysql.rdbms.mysql.datatype.tinyint",
        )
        self.assertEqual(
            assortment.find("./value[@key='isNotNull']").text, "1"
        )
        self.assertEqual(
            assortment.find("./value[@key='defaultValue']").text, "'1'"
        )
        schema = (REPOSITORY / "code/database/schema.sql").read_text(encoding="utf-8")
        self.assertIn("in_assortiment BOOLEAN NOT NULL DEFAULT TRUE", schema)
