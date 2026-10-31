"""Historical invoice records must never be reconstructed with guessed discounts."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import zipfile
import xml.etree.ElementTree as ET

from app import create_app
from domain.business import Invoice
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


def fake_invoice(snapshot=False):
    names = {
        "bedrag_excl_btw": Decimal("40.00"),
        "btw_bedrag": Decimal("3.60"),
        "bedrag_incl_btw": Decimal("43.60"),
        "bestellingskorting": Decimal("0.00"),
        "bedrag_na_bestellingskorting": Decimal("43.60"),
        "eenmalige_korting": Decimal("4.36"),
        "bedrag_na_eenmalige_korting": Decimal("39.24"),
        "klantenkorting": Decimal("1.96"),
        "totaal_bedrag": Decimal("37.28"),
    }
    return {
        "factuur_id": 9, "factuurdatum": date(2026,10,1),
        "betaald_op": None, "bedrijfsnaam": "Testapotheek",
        "adres": "Teststraat 1",
        "lines": [{"quantity":2,"unit_price":Decimal("20.00")}],
        **{key: value if snapshot else None for key,value in names.items()},
    }


class RepositoryStub:
    def __init__(self, snapshot=False):
        self.row=fake_invoice(snapshot)
        self.recorded=[]
    def invoice_for_customer(self, customer_id):
        return [self.row]
    def record_payment_action(self, invoice_id,action,today):
        self.recorded.append((invoice_id,action,today))


class AnnualCursor:
    def __init__(self, annual, paid_count=1, known=1):
        self.responses=[
            {"klant_id":1,"bedrijfsnaam":"Testapotheek"},
            None,
            {"paid_count":paid_count, "known_amount_count":known, "annual":annual}
        ]
        self.queries=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,args): self.queries.append(sql)
    def fetchone(self): return self.responses.pop(0)

class AnnualConnection:
    def __init__(self,annual,paid_count=1,known=1):
        self.c=AnnualCursor(annual,paid_count,known)
    def cursor(self,dictionary=False): return self.c


class SnapshotCursor:
    def __init__(self,existing=None):
        self.existing=existing
        self.sql=[]
        self.params=[]
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def execute(self,sql,args): self.sql.append(sql); self.params.append(args)
    def fetchone(self):
        return {"factuur_id":9,"totaal_bedrag":self.existing}

class SnapshotDB:
    def __init__(self,existing=None):
        self.c=SnapshotCursor(existing)
        self.commits=0
        self.rollbacks=0
    def cursor(self,dictionary=False): return self.c
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1


class HistoricalInvoiceTests(TestCase):
    def test_unpersisted_legacy_displays_unknown_not_fabricated_total(self):
        app=create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-key")
        stub=RepositoryStub(False)
        with patch("routes.administration.get_connection",return_value=object()):
            with patch("routes.administration.AssessedRepository",return_value=stub):
                with app.test_client() as client:
                    resp=client.get("/invoices?customer_id=1")
                    self.assertEqual(resp.status_code,200)
                    self.assertIn(b"Niet vastgelegd",resp.data)
                    self.assertNotIn(b'<option value="mark_paid">',resp.data)
                    self.assertIn(b"40.00",resp.data)
                    resp=client.post("/invoices/actions",data={
                        "invoice_id":"9","customer_id":"1","action":"mark_paid",
                        "received_amount":"40.00"
                    })
                    self.assertEqual(resp.status_code,400)
        self.assertFalse(stub.recorded)

    def test_all_invoice_actions_check_customer_ownership(self):
        app=create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-key")
        stub=RepositoryStub(True)
        with patch("routes.administration.get_connection",return_value=object()):
            with patch("routes.administration.AssessedRepository",return_value=stub):
                with app.test_client() as client:
                    for action in ("reminder1", "reminder2", "payment_plan_accepted",
                                   "payment_plan_rejected", "mark_paid"):
                        response=client.post("/invoices/actions",data={
                            "invoice_id":"10", "customer_id":"1",
                            "action":action, "received_amount":"37.28",
                        })
                        self.assertEqual(response.status_code,400,action)
        self.assertEqual(stub.recorded,[])

    def test_persisted_invoice_total_is_checked_without_recalculation(self):
        app=create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-key")
        stub=RepositoryStub(True)
        with patch("routes.administration.get_connection",return_value=object()):
            with patch("routes.administration.AssessedRepository",return_value=stub):
                with app.test_client() as client:
                    resp=client.get("/invoices?customer_id=1")
                    self.assertIn(b'<option value="mark_paid">',resp.data)
                    self.assertIn(b"37.28",resp.data)
                    wrong=client.post("/invoices/actions",data={
                        "invoice_id":"9","customer_id":"1","action":"mark_paid",
                        "received_amount":"43.60"
                    })
                    self.assertEqual(wrong.status_code,400)
                    correct=client.post("/invoices/actions",data={
                        "invoice_id":"9","customer_id":"1","action":"mark_paid",
                        "received_amount":"37.28"
                    })
                    self.assertEqual(correct.status_code,302)
        self.assertEqual(stub.recorded[0][0:2],(9,"mark_paid"))

    def test_annual_discount_uses_net_amounts_of_paid_invoices(self):
        db=AnnualConnection(Decimal("12000.00"),paid_count=3,known=3)
        customer,annual=AssessedRepository(db).customer_revenue(1,2025)
        self.assertEqual(annual,Decimal("12000.00"))
        self.assertIn("SUM(f.totaal_bedrag)",db.c.queries[2])
        incomplete=AnnualConnection(Decimal("1000.00"),paid_count=2,known=1)
        with self.assertRaises(DomainError):
            AssessedRepository(incomplete).customer_revenue(1,2025)

    def test_invoice_case_includes_intermediate_discount_totals(self):
        doc=Invoice(1,"INV-1",date(2026,10,1)).createWeeklyInvoice(
            "Testapotheek","Teststraat 1",
            [{"quantity":2,"unit_price":Decimal("20.00")}],
            annualRevenue=0,firstOrder=True)
        self.assertEqual(doc["total_ex_vat"],Decimal("40.00"))
        self.assertEqual(doc["vat_9_percent"],Decimal("3.60"))
        self.assertEqual(doc["total_after_order_discount"],Decimal("43.60"))
        self.assertEqual(doc["total_after_first_order_discount"],Decimal("39.24"))
        self.assertEqual(doc["total"],Decimal("37.28"))

    def test_invoice_snapshot_written_once_from_explicit_calculation(self):
        doc=Invoice(1,"INV-1",date(2026,10,1)).createWeeklyInvoice(
            "Testapotheek","Teststraat 1",
            [{"quantity":2,"unit_price":Decimal("20.00")}],
            annualRevenue=0,firstOrder=True)
        db=SnapshotDB()
        AssessedRepository(db).save_invoice_snapshot(9,doc)
        self.assertEqual(db.commits,1)
        self.assertEqual(db.rollbacks,0)
        self.assertEqual(len(db.c.params[-1]),10)
        self.assertEqual(db.c.params[-1][-1],9)
        self.assertEqual(db.c.params[-1][-2],Decimal("37.28"))
        existing=SnapshotDB(existing=Decimal("37.28"))
        with self.assertRaises(DomainError):
            AssessedRepository(existing).save_invoice_snapshot(9,doc)
        self.assertEqual(existing.commits,0)
        self.assertEqual(existing.rollbacks,1)

    def test_invoice_eer_contains_all_nullable_snapshot_columns(self):
        repo=Path(__file__).resolve().parents[2]
        with zipfile.ZipFile(repo/"eer.mwb") as z:
            self.assertIsNone(z.testzip())
            root=ET.fromstring(z.read("document.mwb.xml"))
        tables=[n for n in root.iter("value") if n.get("struct-name")=="db.mysql.Table"]
        invoice=next(n for n in tables if n.find("./value[@key='name']").text=="factuur")
        cols={n.find("./value[@key='name']").text:n for n in invoice.iter("value")
              if n.get("struct-name")=="db.mysql.Column"}
        for name in ("bedrag_excl_btw","btw_bedrag","bedrag_incl_btw","bestellingskorting",
                     "bedrag_na_bestellingskorting","eenmalige_korting",
                     "bedrag_na_eenmalige_korting","klantenkorting","totaal_bedrag"):
            self.assertIn(name,cols)
            self.assertEqual(cols[name].find("./value[@key='isNotNull']").text,"0")
            self.assertEqual(
                cols[name].find("./link[@key='simpleType']").text,
                "com.mysql.rdbms.mysql.datatype.decimal")
