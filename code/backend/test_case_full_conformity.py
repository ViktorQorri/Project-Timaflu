"""Regression tests for case-authoritative acquisition, invoicing and delivery."""
from datetime import date, time
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.acquisition_repository import AcquisitionRepository
from test_acquisition import FakeConnection as AcquisitionFakeConnection
from test_case_courier_prospects import Connection as DeliveryConnection


class CaseCursor:
    def __init__(self, connection):
        self.db = connection
        self.lastrowid = 0
        self.last = ""
        self.rowcount = 1
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params=()):
        self.last = " ".join(sql.split())
        self.db.statements.append((self.last, tuple(params)))
        if self.last.startswith("INSERT INTO"):
            self.lastrowid += 1
    def fetchone(self):
        q = self.last
        if "SELECT klant_id, opvolging_afgesloten FROM PotentieleKlant" in q:
            return {"klant_id": self.db.customer_id,
                    "opvolging_afgesloten": self.db.closed}
        if "SELECT MAX(bezoekdatum)" in q:
            return {"laatste_bezoek": self.db.visited}
        if "SELECT COUNT(*) AS aantal FROM Bestelling" in q:
            return {"aantal": self.db.orders}
        if "SELECT b.bestelling_id, r.ritdatum FROM Bestelling" in q:
            return {"bestelling_id": 1, "ritdatum": date(2026, 10, 31)} if self.db.failed_delivery else None
        if "SELECT * FROM PotentieleKlant" in q:
            return {"klant_id": self.db.customer_id, "opvolging_afgesloten": self.db.closed,
                    "bedrijfsnaam": "Apotheek", "contactgegevens": "0612345678",
                    "contactpersoon": "Test"}
        if "FROM Factuur f WHERE f.factuur_id" in q:
            return {"factuur_id": 1, "klant_id": 1,
                    "factuurdatum": date(2026, 10, 1), "betaald_op": self.db.paid}
        return None
    def fetchall(self): return []


class CaseDB:
    def __init__(self, visited=date(2026, 9, 1), customer_id=None,
                 orders=0, closed=False, paid=None, failed_delivery=True):
        self.failed_delivery = failed_delivery
        self.visited = visited
        self.customer_id = customer_id
        self.orders = orders
        self.closed = closed
        self.paid = paid
        self.statements = []
        self.c = CaseCursor(self)
        self.commits = 0
        self.rollbacks = 0
    def cursor(self, dictionary=False): return self.c
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


class CaseConformityTests(TestCase):
    def test_decline_closes_followup_after_one_month(self):
        # Current AD21 implementation is AcquisitionRepository, not the old assessed stub.
        db = AcquisitionFakeConnection(rows=[
            {"klant_id": None, "opvolging_afgesloten": False, "bedrijfsnaam": "Apotheek"},
            {"is_due": 1}, None,
        ])
        self.assertIsNone(AcquisitionRepository(db).complete_follow_up(1, "no_interest"))
        self.assertEqual(db.commits, 1)
        self.assertTrue(any("opvolging_afgesloten = TRUE" in sql
                            for sql,_ in db.cursor_instance.statements))

    def test_early_decline_is_rejected(self):
        db = AcquisitionFakeConnection(rows=[
            {"klant_id": None, "opvolging_afgesloten": False, "bedrijfsnaam": "Apotheek"},
            {"is_due": 0},
        ])
        with self.assertRaises(DomainError):
            AcquisitionRepository(db).complete_follow_up(1, "no_interest")
        self.assertEqual((db.commits, db.rollbacks), (0,1))

    def test_decline_does_not_run_for_existing_order(self):
        db = AcquisitionFakeConnection(rows=[
            {"klant_id": 2, "opvolging_afgesloten": False, "bedrijfsnaam": "Apotheek"},
            {"is_due": 1}, {"bestelling_id": 9},
        ])
        with self.assertRaises(DomainError):
            AcquisitionRepository(db).complete_follow_up(1, "no_interest")
        self.assertEqual((db.commits, db.rollbacks), (0,1))

    def test_prospect_conversion_persists_incentive_and_ends_acquisition(self):
        db = CaseDB()
        customer_id = AssessedRepository(db).register_prospect_customer(
            3, "Factuuradres", "Afleveradres")
        self.assertGreater(customer_id, 0)
        self.assertEqual(db.commits, 1)
        stmts = [q for q,_ in db.statements]
        self.assertTrue(any("eenmalige_korting_toegezegd" in q and "TRUE" in q
                            for q in stmts))
        self.assertTrue(any("klant_id=%s, opvolging_afgesloten=TRUE" in q
                            for q in stmts))
        premature = CaseDB(visited=date.today())
        with self.assertRaises(DomainError):
            AssessedRepository(premature).register_prospect_customer(
                3, "Factuuradres", "Afleveradres")
        self.assertEqual(premature.commits, 0)
        linked = CaseDB(customer_id=9)
        with self.assertRaises(DomainError):
            AssessedRepository(linked).register_prospect_customer(
                3, "Factuuradres", "Afleveradres")

    def test_followup_and_paid_invoice_queries(self):
        db = CaseDB()
        repo = AssessedRepository(db)
        repo.prospect_followups(date(2026, 9, 30))
        self.assertIn("p.opvolging_afgesloten=FALSE", db.statements[-1][0])
        self.assertIn("NOT EXISTS", db.statements[-1][0])
        repo.invoice_for_customer(1)
        self.assertIn("f.betaald_op IS NULL", db.statements[-1][0])

    def test_payment_plan_only_after_three_unpaid_weeks(self):
        early = CaseDB()
        with self.assertRaises(DomainError):
            AssessedRepository(early).record_payment_action(
                1, "payment_plan_accepted", date(2026, 10, 10))
        self.assertEqual(early.commits, 0)
        mature = CaseDB()
        AssessedRepository(mature).record_payment_action(
            1, "payment_plan_accepted", date(2026, 10, 22))
        self.assertEqual(mature.commits, 1)

    def test_paid_invoice_cannot_be_marked_paid_twice(self):
        db = CaseDB(paid=date(2026, 10, 20))
        with self.assertRaises(DomainError):
            AssessedRepository(db).record_payment_action(
                1, "mark_paid", date(2026, 10, 31))
        self.assertFalse(any("SET betaald_op" in q for q,_ in db.statements))

    def test_retry_must_be_later_that_day(self):
        from test_distribution import FakeConnection
        for invalid in (time(9),time(10),time(18)):
            db=FakeConnection(one_rows=[{
                "resultaat":None,"geplande_tijd":time(10),"rit_id":5
            }])
            with self.assertRaises(DomainError):
                AssessedRepository(db).register_first_delivery_attempt(
                    4,date(2026,10,30),False,False,invalid
                )
            self.assertEqual(db.commits,0)
        allowed=FakeConnection(one_rows=[{
            "resultaat":None,"geplande_tijd":time(10),"rit_id":5
        }])
        AssessedRepository(allowed).register_first_delivery_attempt(
            4,date(2026,10,30),False,False,time(14)
        )
        self.assertEqual(allowed.commits,1)

    def test_failed_delivery_followup_rejects_unconfirmed_or_invalid_plan(self):
        missing = CaseDB(failed_delivery=False)
        with self.assertRaises(DomainError):
            AssessedRepository(missing).record_failed_delivery_followup(
                1, date(2026, 11, 2), "ochtend", 5, "Extra rit")
        self.assertEqual(missing.commits, 0)
        valid = CaseDB()
        with self.assertRaises(DomainError):
            AssessedRepository(valid).record_failed_delivery_followup(
                1, date(2026, 10, 31), "ochtend", 5, "Extra rit")
        with self.assertRaises(DomainError):
            AssessedRepository(valid).record_failed_delivery_followup(
                1, date(2026, 11, 2), "middag", 5, "")
        with self.assertRaises(DomainError):
            AssessedRepository(valid).record_failed_delivery_followup(
                1, date(2026, 11, 2), "middag", -1, "Kosten")
        self.assertEqual(valid.commits, 0)
        AssessedRepository(valid).record_failed_delivery_followup(
            1, date(2026, 11, 2), "ochtend", "10.00", "Tweemaal afwezig")
        self.assertEqual(valid.commits, 1)
        self.assertTrue(any("extra_bezorgkosten" in sql
                            for sql,_ in valid.statements))

    def test_decline_form_requires_explicit_confirmation(self):
        app=create_app()
        app.config.update(TESTING=True,SECRET_KEY="test")
        prospect={
            "potentiele_klant_id":3,"bedrijfsnaam":"Apotheek",
            "contactpersoon":"Contact","contactgegevens":"06123",
            "adres":"Teststraat 1","laatste_bezoek":date(2026,9,1)
        }
        with patch("routes.acquisition._service") as service:
            service.return_value.due_follow_ups.return_value=[prospect]
            service.return_value.complete_follow_up.return_value=None
            with app.test_client() as client:
                screen=client.get("/acquisition")
                self.assertEqual(screen.status_code,200)
                self.assertIn(b'name="decision_confirmed"',screen.data)
                bad=client.post("/acquisition/prospects/3/follow-up",data={"outcome":"no_interest"})
                self.assertEqual(bad.status_code,400)
                good=client.post("/acquisition/prospects/3/follow-up",data={
                    "outcome":"no_interest","decision_confirmed":"yes"
                })
                self.assertEqual(good.status_code,302)
            service.return_value.complete_follow_up.assert_called_once()
            args=service.return_value.complete_follow_up.call_args.args
            self.assertEqual(args[0],3)
            self.assertEqual(dict(args[1]),{
                "outcome":"no_interest","decision_confirmed":"yes"
            })

    def test_measured_query_samples_mirror_screen_fields(self):
        root=Path(__file__).resolve().parents[2]
        examples=(root/"Documentation/Architecture/test-data/selects_assessed.sql").read_text(encoding="utf-8")
        for fragment in ("k.eenmalige_korting_toegezegd",
                         "a.adres AS klantadres",
                         "f.betalingsregeling_geaccepteerd",
                         "f.incasso_ingeschakeld",
                         "f.betaald_op IS NULL",
                         "p.opvolging_afgesloten=FALSE"):
            self.assertIn(fragment,examples)

    def test_mobile_distribution_is_semantically_labelled_without_javascript(self):
        root=Path(__file__).resolve().parents[2]
        html=(root/"code/frontend/templates/deliveries.html").read_text(encoding="utf-8")
        css=(root/"code/frontend/static/css/deliveries.css").read_text(encoding="utf-8")
        base=(root/"code/frontend/templates/base.html").read_text(encoding="utf-8")
        for label in ("Tijd", "Bestelling", "Klant", "Adres", "Contact",
                      "Status", "Afhandeling"):
            self.assertIn('data-label="'+label+'"',html)
        self.assertIn("@media (max-width: 720px)",css)
        self.assertIn("grid-template-columns",css)
        self.assertIn("{% block extra_styles %}",base)
        self.assertIn("css/deliveries.css",html)
        self.assertNotIn("<script",html.lower())
        self.assertNotIn("onclick=",html.lower())

    def test_acquisition_columns_exist_in_schema_and_eer(self):
        root=Path(__file__).resolve().parents[2]
        schema=(root/"code/database/schema.sql").read_text(encoding="utf-8")
        migration=(root/"code/database/migrations/2026_10_31_acquisition_followup.sql").read_text(encoding="utf-8")
        names={"klant":"eenmalige_korting_toegezegd",
               "potentieleklant":"opvolging_afgesloten"}
        with zipfile.ZipFile(root/"eer.mwb") as zip_file:
            self.assertIsNone(zip_file.testzip())
            document=ET.fromstring(zip_file.read("document.mwb.xml"))
        for table_name,column_name in names.items():
            self.assertIn(column_name+" BOOLEAN NOT NULL DEFAULT FALSE",schema)
            self.assertIn(column_name+" BOOLEAN NOT NULL DEFAULT FALSE",migration)
            table=next(t for t in document.iter("value")
                       if t.get("struct-name")=="db.mysql.Table"
                       and t.find("./value[@key='name']") is not None
                       and t.find("./value[@key='name']").text==table_name)
            self.assertTrue(any(c.get("struct-name")=="db.mysql.Column"
                                and c.find("./value[@key='name']") is not None
                                and c.find("./value[@key='name']").text==column_name
                                for c in table.iter("value")))
