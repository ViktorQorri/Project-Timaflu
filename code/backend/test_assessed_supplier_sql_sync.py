"""Ensure supplier lookup and example SQL use the same case-mandated filter."""
from pathlib import Path
from unittest import TestCase

from repositories.supplier_repository import SupplierRepository


class SupplierSqlSyncTests(TestCase):
    def test_internal_reorder_list_is_filtered_consistently(self):
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, query, args): self.query=query
            def fetchall(self): return []
        class DB:
            def __init__(self): self.cursor_instance=Cursor()
            def cursor(self, dictionary=False): return self.cursor_instance
        db=DB()
        SupplierRepository(db).find_offers("Medication")
        sample=(Path(__file__).resolve().parents[1]/"database/queries.sql").read_text(encoding="utf-8")
        expected="WHERE p.productnaam LIKE %s AND p.intern_bestelbaar = TRUE"
        self.assertIn(expected,db.cursor_instance.query)
        self.assertIn(
            "WHERE p.productnaam LIKE '%Medication%' AND p.intern_bestelbaar = TRUE",sample
        )
        self.assertIn("UPDATE Product SET intern_bestelbaar=FALSE WHERE product_id=1;",sample)
