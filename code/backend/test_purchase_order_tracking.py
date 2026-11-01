"""Verify that purchase tracking preserves unknown legacy dates and statuses."""

from pathlib import Path
from unittest import TestCase
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[2]


class PurchaseOrderTrackingTests(TestCase):
    def test_schema_and_migration_leave_existing_values_unknown(self):
        schema = (ROOT / "code/database/schema.sql").read_text(encoding="utf-8")
        migration = (
            ROOT / "code/database/migrations/2026_10_31_purchase_order_tracking.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("besteld_op DATETIME NULL", schema)
        self.assertIn("status_naam VARCHAR(30) NULL", schema)
        self.assertIn("besteld_op DATETIME NULL", migration)
        self.assertIn("status_naam VARCHAR(30) NULL", migration)
        self.assertNotIn("UPDATE Inkoopbestelling", migration)

    def test_repository_queries_are_documented(self):
        repository = (
            ROOT / "code/backend/repositories/purchase_order_repository.py"
        ).read_text(encoding="utf-8")
        queries = (ROOT / "code/database/queries.sql").read_text(encoding="utf-8")
        repository_sql = " ".join(repository.split())
        normalized = " ".join(queries.split())
        recorded_query = (
            "SELECT i.inkoopbestelling_id, i.besteld_op, i.status_naam, "
            "l.naam AS leverancier, p.productnaam, r.aantal "
            "FROM Inkoopbestelling AS i "
            "JOIN Leverancier AS l ON l.leverancier_id = i.leverancier_id "
            "JOIN Inkoopbestelregel AS r "
            "ON r.inkoopbestelling_id = i.inkoopbestelling_id "
            "JOIN Product AS p ON p.product_id = r.product_id "
            "ORDER BY i.besteld_op DESC, i.inkoopbestelling_id DESC, "
            "p.productnaam"
        )
        self.assertIn(recorded_query, repository_sql)
        self.assertIn(recorded_query, normalized)
        self.assertIn(
            "INSERT INTO Inkoopbestelling (leverancier_id, besteld_op, status_naam) "
            "VALUES (%s, CURRENT_TIMESTAMP, 'besteld')",
            repository_sql,
        )
        self.assertIn(
            "INSERT INTO Inkoopbestelling (leverancier_id, besteld_op, status_naam) "
            "VALUES (1, CURRENT_TIMESTAMP, 'besteld')",
            normalized,
        )

    def test_eer_model_contains_purchase_tracking_columns(self):
        with zipfile.ZipFile(ROOT / "eer.mwb") as archive:
            self.assertIsNone(archive.testzip())
            root = ET.fromstring(archive.read("document.mwb.xml"))
        table = next(
            node
            for node in root.iter("value")
            if node.get("struct-name") == "db.mysql.Table"
            and node.find("./value[@key='name']").text == "inkoopbestelling"
        )
        columns = {
            column.find("./value[@key='name']").text
            for column in table.iter("value")
            if column.get("struct-name") == "db.mysql.Column"
        }
        self.assertIn("besteld_op", columns)
        self.assertIn("status_naam", columns)
