"""Verify the non-persisted invoice calculation with representative data."""
from pathlib import Path
import sqlite3
from decimal import Decimal
from unittest import TestCase

SQL = (Path(__file__).resolve().parents[1] / "database" / "schema.sql").read_text(encoding="utf-8")
VIEW = "CREATE VIEW FactuurOverzicht AS" + SQL.split("CREATE VIEW FactuurOverzicht AS", 1)[1].split(";", 1)[0] + ";"


class ThreeNormalFormInvoiceTests(TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("""CREATE TABLE Factuur (
            factuur_id INTEGER PRIMARY KEY, bedrag_excl_btw NUMERIC,
            btw_bedrag NUMERIC, bestellingskorting NUMERIC,
            eenmalige_korting NUMERIC, klantenkorting NUMERIC,
            extra_bezorgkosten_excl_btw NUMERIC NOT NULL DEFAULT 0,
            extra_bezorgkosten_btw NUMERIC NOT NULL DEFAULT 0)""")
        self.db.executescript(VIEW)

    def tearDown(self):
        self.db.close()

    def test_all_intermediate_and_final_values_derive_from_base(self):
        self.db.execute("""INSERT INTO Factuur VALUES (1, 40, 3.60, 0, 4.36, 1.96, 10, 0.90)""")
        row = self.db.execute("""SELECT bedrag_incl_btw, bedrag_na_bestellingskorting,
            bedrag_na_eenmalige_korting, extra_bezorgkosten_incl_btw, totaal_bedrag
            FROM FactuurOverzicht WHERE factuur_id=1""").fetchone()
        self.assertEqual(tuple(Decimal(str(v)).quantize(Decimal("0.01")) for v in row),
                         tuple(map(Decimal, ("43.60", "43.60", "39.24", "10.90", "48.18"))))

    def test_unknown_historical_snapshot_stays_unknown(self):
        self.db.execute("INSERT INTO Factuur (factuur_id) VALUES (2)")
        self.assertIsNone(self.db.execute(
            "SELECT totaal_bedrag FROM FactuurOverzicht WHERE factuur_id=2"
        ).fetchone()[0])

    def test_base_table_has_no_derived_columns(self):
        columns={row[1] for row in self.db.execute("PRAGMA table_info(Factuur)")}
        self.assertFalse(columns.intersection({
            "totaal_bedrag", "bedrag_incl_btw", "bedrag_na_bestellingskorting",
            "bedrag_na_eenmalige_korting", "extra_bezorgkosten_incl_btw"
        }))
