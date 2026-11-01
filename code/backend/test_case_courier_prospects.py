"""Regression checks for required Timaflu case scenarios.

Checks the two-stage same-day courier retry and prospect order check.
Does not invent additional business states or database schema.
"""
from datetime import date,time
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch
from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


class Cursor:
    def __init__(self, state):
        self.state = state
        self.statements=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,params=()):
        self.statements.append((" ".join(sql.split()),tuple(params)))
        if "UPDATE Leverpoging SET resultaat='niet aanwezig'" in sql:
            self.state["first"] = "niet aanwezig"
        elif "INSERT INTO Leverpoging" in sql:
            self.state["second_exists"]=True
        elif "UPDATE Leverpoging SET resultaat=%s" in sql:
            self.state["second_result"]=params[0]
            self.state["signed"]=params[1]
    def fetchone(self):
        query=self.statements[-1][0]
        if "SELECT lp.rit_id, lp.pogingnummer" in query:
            return {"rit_id": 5, "pogingnummer": 1, "resultaat": self.state.get("first"),
                    "first_attempt_seconds": 10 * 3600}
        if "SELECT lp.resultaat" in query:
            return {"resultaat":self.state.get("second_result")} if self.state.get("second_exists") else None
        raise AssertionError(query)

class Connection:
    def __init__(self,initial=None):
        self.state={"first":None,"second_exists":False,"second_result":None}
        if initial:self.state.update(initial)
        self.cursor_instance=Cursor(self.state)
        self.commits=0;self.rollbacks=0
    def cursor(self,dictionary=False):return self.cursor_instance
    def commit(self):self.commits+=1
    def rollback(self):self.rollbacks+=1

class CaseProcessTests(TestCase):
    def test_schedule_first_absence_keeps_second_visit_pending(self):
        from test_distribution import FakeConnection
        db=FakeConnection(one_rows=[{
            "resultaat":None,"geplande_tijd":time(10),"rit_id":5,
        }])
        AssessedRepository(db).register_first_delivery_attempt(
            4,date(2026,10,30),False,False,time(14)
        )
        statements=db.cursor_instance.statements
        insert=next((query,params) for query,params in statements
                    if "INSERT INTO Leverpoging" in query)
        self.assertIn("NULL, FALSE",insert[0])
        self.assertEqual(insert[1],(4,5,time(14)))
        self.assertEqual(db.commits,1)
        self.assertFalse(any("INSERT INTO Leveringregel" in q for q,_ in statements))

    def test_second_visit_must_be_later_on_the_same_day(self):
        from test_distribution import FakeConnection
        for invalid in (time(9),time(10),time(18)):
            db=FakeConnection(one_rows=[{
                "resultaat":None,"geplande_tijd":time(10),"rit_id":5,
            }])
            with self.subTest(invalid=invalid),self.assertRaises(DomainError):
                AssessedRepository(db).register_first_delivery_attempt(
                    4,date(2026,10,30),False,False,invalid
                )
            self.assertEqual(db.commits,0)
            self.assertEqual(db.rollbacks,1)

    def test_outcome_requires_explicit_signature_and_pending_second_visit(self):
        db=Connection({"second_exists":True})
        with self.assertRaises(DomainError):
            AssessedRepository(db).record_second_attempt_outcome(4,date(2026,10,30),"afgeleverd",None)
        self.assertEqual(db.commits,0)
        AssessedRepository(db).record_second_attempt_outcome(4,date(2026,10,30),"afgeleverd","yes")
        self.assertEqual(db.state["second_result"],"afgeleverd")
        self.assertTrue(db.state["signed"])
        self.assertEqual(db.commits,1)
        with self.assertRaises(DomainError):
            AssessedRepository(db).record_second_attempt_outcome(4,date(2026,10,30),"afgeleverd","yes")

    def test_second_absence_is_a_final_distinct_outcome(self):
        db=Connection({"second_exists":True})
        AssessedRepository(db).record_second_attempt_outcome(4,date(2026,10,30),"niet aanwezig",None)
        self.assertFalse(db.state["signed"])
        self.assertEqual(db.state["second_result"],"niet aanwezig")
        self.assertTrue(any("status_naam='niet afgeleverd'" in q
                            for q,_ in db.cursor_instance.statements))

    def test_courier_web_routes_are_separate(self):
        app=create_app()
        app.config.update(TESTING=True,SECRET_KEY="test-only")
        class Stub:
            def __init__(self):self.first=[];self.second=[]
            def register_first_delivery_attempt(self,*args):self.first.append(args)
            def register_delivery_attempt(self,*args):self.second.append(args)
        stub=Stub()
        with patch("routes.distribution.get_connection",return_value=object()):
            with patch("routes.distribution.AssessedRepository",return_value=stub):
                with app.test_client() as client:
                    first=client.post("/deliveries/first-attempt",data={
                        "day":"2026-10-30","delivery_id":4,"outcome":"niet aanwezig",
                        "second_time":"14:00"
                    })
                    self.assertEqual(first.status_code,302)
                    self.assertEqual(stub.first[0],(4,date(2026,10,30),False,False,time(14)))
                    second=client.post("/deliveries/second-attempt",data={
                        "day":"2026-10-30","delivery_id":4,"time":"14:00",
                        "outcome":"afgeleverd","receipt_signed":"1"
                    })
                    self.assertEqual(second.status_code,302)
                    self.assertEqual(stub.second[0],(4,date(2026,10,30),True,time(14),True))

    def test_acquisition_visit_requires_contact_details_and_valid_date(self):
        app=create_app()
        app.config.update(TESTING=True,SECRET_KEY="test-only")
        with app.test_client() as client:
            cases=(
                {"company_name":"Apotheek","address":"Straat","visit_date":"2026-10-01"},
                {"company_name":"Apotheek","contact_person":"Persoon",
                 "address":"Straat","visit_date":"2026-10-01"},
                {"company_name":"Apotheek","contact_person":"Persoon",
                 "contact_details":"06123","address":"Straat","visit_date":"ongeldig"},
            )
            for invalid in cases:
                response=client.post("/acquisition/prospects",data=invalid)
                self.assertEqual(response.status_code,400,invalid)
        source=app.jinja_loader.get_source(app.jinja_env,"acquisition.html")[0]
        self.assertIn('name="contact_person"',source)
        self.assertIn('name="contact_details"',source)

    def test_prospect_sql_checks_actual_order_not_just_account(self):
        from pathlib import Path
        import inspect
        source=inspect.getsource(AssessedRepository.prospect_followups)
        self.assertIn("NOT EXISTS",source)
        self.assertIn("Bestelling b WHERE b.klant_id = p.klant_id",source)
        self.assertNotIn("p.klant_id IS NULL",source)
        doc=(Path(__file__).resolve().parents[1]/"database/queries.sql").read_text(encoding="utf-8")
        self.assertIn("NOT EXISTS",doc)
        self.assertIn("Bestelling b WHERE b.klant_id = p.klant_id",doc)

    def test_invoice_screen_matches_required_amount_breakdown(self):
        app=create_app()
        app.config.update(TESTING=True)
        sample={
          "invoice_number":17,"date":date(2026,10,30),"customer_name":"Testapotheek",
          "customer_address":"Voorbeeldstraat 1",
          "lines":[{"quantity":2,"unit_price":Decimal("10.00"),"line_total":Decimal("20.00")}],
          "total_ex_vat":Decimal("20.00"),"vat_9_percent":Decimal("1.80"),
          "total_incl_vat":Decimal("21.80"),"order_discount":Decimal("0"),
          "total_after_order_discount":Decimal("21.80"),
          "first_order_discount":Decimal("2.18"),
          "total_after_first_order_discount":Decimal("19.62"),
          "customer_discount":Decimal("0.98"),"total":Decimal("18.64"),
          "snapshot_complete":True,"action":"no_action",
          "extra_delivery_costs":Decimal("0.00"),
        }
        with app.test_request_context("/invoices?customer_id=1"):
            html=app.jinja_env.get_template("invoices.html").render(
                invoices=[sample],customer_id=1,today="2026-10-30",
                purchase_invoices=[],uninvoiced_deliveries=[]
            )
        for label in ("Totaal excl. btw","9% btw","Totaal incl. btw",
                      "Bestellingskorting","Eenmalige korting","Klantenkorting"):
            self.assertIn(label,html)
        self.assertIn("Testapotheek",html)
        self.assertIn("Voorbeeldstraat 1",html)
