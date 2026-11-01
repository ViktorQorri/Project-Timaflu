"""Regression check: new schema and upgrade migration enforce identical invoice arithmetic."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "database"


def test_invoice_snapshot_constraints_present():
    for source in (ROOT / "schema.sql", ROOT / "migrations" / "2026_11_01_invoice_snapshot_integrity.sql"):
        sql = source.read_text(encoding="utf-8")
        assert "ck_factuur_btw_totaal" in sql
        assert "bedrag_incl_btw = bedrag_excl_btw + btw_bedrag" in sql
        assert "ck_factuur_bezorgkosten_totaal" in sql
        assert "extra_bezorgkosten_excl_btw + extra_bezorgkosten_btw" in sql
