"""Issue #57: purchase-order tracking must not invent historical status or dates."""
from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]

class PurchaseTrackingTests(unittest.TestCase):
    def test_purchase_schema_retains_legacy_unknown_fields(self):
        sql=(ROOT/"code/database/schema.sql").read_text(encoding="utf-8")
        migration=(ROOT/"code/database/migrations/2026_10_31_purchase_order_tracking.sql").read_text(encoding="utf-8")
        self.assertIn("besteld_op DATETIME NULL",sql)
        self.assertIn("status_naam VARCHAR(30) NULL",sql)
        self.assertIn("besteld_op DATETIME NULL",migration)
        self.assertIn("status_naam VARCHAR(30) NULL",migration)
        self.assertNotIn("UPDATE Inkoopbestelling",migration)

    def test_sql_records_actual_new_order_timestamp_and_status(self):
        from repositories.purchase_order_repository import PurchaseOrderRepository
        class C:
            def __init__(self): self.statements=[];self.lastrowid=7
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def execute(self,sql,params=()): self.statements.append(sql)
            def fetchone(self): return (1,)
        class DB:
            def __init__(self): self.c=C()
            def cursor(self,*args,**kwargs): return self.c
            def commit(self): pass
            def rollback(self): pass
        db=DB()
        self.assertEqual(PurchaseOrderRepository(db).create(1,2,3),7)
        self.assertTrue(any(
            "CURRENT_TIMESTAMP" in sql and "status_naam" in sql and "'besteld'" in sql
            for sql in db.c.statements
        ))
        doc=(ROOT/"code/database/queries.sql").read_text(encoding="utf-8")
        self.assertIn("INSERT INTO Inkoopbestelling (leverancier_id, besteld_op, status_naam)",doc)

    def test_workbench_eer_tracks_same_columns(self):
        with zipfile.ZipFile(ROOT/"eer.mwb") as z:
            self.assertIsNone(z.testzip())
            xml=ET.fromstring(z.read("document.mwb.xml"))
        tables=[t for t in xml.iter("value") if t.get("struct-name")=="db.mysql.Table"]
        purchase=next(t for t in tables if t.find("./value[@key='name']").text=="inkoopbestelling")
        columns=[c.find("./value[@key='name']").text for c in purchase.iter("value")
                 if c.get("struct-name")=="db.mysql.Column"]
        self.assertIn("besteld_op",columns)
        self.assertIn("status_naam",columns)
