"""Regression checks for required Timaflu case scenarios.

Checks the two-stage same-day courier retry and prospect order check.
Does not invent additional business states or database schema.
"""
from datetime import date,time
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
        db=Connection()
        AssessedRepository(db).schedule_second_attempt(4,time(14,0),date(2026,10,30))
        self.assertEqual(db.state["first"],"niet aanwezig")
        self.assertTrue(db.state["second_exists"])
        self.assertIsNone(db.state["second_result"])
        self.assertEqual(db.commits,1)
        self.assertIn("VALUES (%s,2,%s,%s,NULL,NULL)",db.cursor_instance.statements[-1][0])
        self.assertEqual(db.cursor_instance.statements[0][1],(4,date(2026,10,30)))

    def test_second_visit_must_be_later_on_the_same_day(self):
        for invalid_time in (time(9, 0), time(10, 0)):
            db = Connection()
            with self.assertRaises(DomainError):
                AssessedRepository(db).schedule_second_attempt(
                    4, invalid_time, date(2026, 10, 30)
                )
            self.assertEqual(db.commits, 0)
            self.assertFalse(db.state["second_exists"])
            self.assertEqual(db.state["first"], None)

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
        class MockService:
            def __init__(self):self.scheduled=[];self.finished=[]
            def schedule_second_attempt(self,*args):self.scheduled.append(args)
            def record_second_attempt_outcome(self,*args):self.finished.append(args)
        service=MockService()
        with patch("routes.distribution.get_connection",return_value=object()):
            with patch("routes.distribution.AssessedRepository",return_value=service):
                with app.test_client() as client:
                    r=client.post("/deliveries/second-attempt",data={
                        "day":"2026-10-30","delivery_id":4,"time":"14:00"
                    })
                    self.assertEqual(r.status_code,302)
                    self.assertEqual(service.scheduled[0],(4,time(14),date(2026,10,30)))
                    r=client.post("/deliveries/second-attempt/result",data={
                        "day":"2026-10-30","delivery_id":4,
                        "outcome":"afgeleverd","signature_confirmed":"yes"
                    })
                    self.assertEqual(r.status_code,302)
                    self.assertEqual(service.finished[0],(4,date(2026,10,30),"afgeleverd","yes"))

    def test_acquisition_visit_requires_contact_details_and_valid_date(self):
        app=create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-only")
        with app.test_client() as client:
            for invalid in (
                {"company":"Apotheek", "address":"Straat", "visit_date":"2026-10-01"},
                {"company":"Apotheek", "contact":"Persoon", "address":"Straat", "visit_date":"2026-10-01"},
                {"company":"Apotheek", "contact":"Persoon", "details":"06123", "address":"Straat", "visit_date":"ongeldig"},
            ):
                response=client.post("/acquisition/visits", data=invalid)
                self.assertEqual(response.status_code,400, invalid)
        source=(app.jinja_loader.get_source(app.jinja_env,"acquisition.html"))[0]
        self.assertIn('name="contact" required', source)
        self.assertIn('name="details" required', source)

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
          "lines":[{"quantity":2,"unit_price":"10.00","line_total":"20.00"}],
          "total_ex_vat":"20.00","vat_9_percent":"1.80","total_incl_vat":"21.80",
          "order_discount":"0.00","total_after_order_discount":"21.80",
          "first_order_discount":"2.18","total_after_first_order_discount":"19.62",
          "customer_discount":"0.98","total":"18.64","snapshot_complete":True,
          "action":"no_action"
        }
        with app.test_request_context("/invoices?customer_id=1"):
            html=app.jinja_env.get_template("invoices.html").render(
                invoices=[sample],customer_id=1
            )
        for label in ("Datum","Factuurnummer","Timaflu","Totaal excl. btw",
                      "9% btw","Totaal incl. btw","Bestellingskorting",
                      "Eenmalige korting","Klantenkorting","Totaal incl. klantenkorting"):
            self.assertIn(label,html)
        self.assertIn("Voorbeeldstraat 1",html)
        self.assertIn("afzenderadres: niet opgenomen in de casus",html.lower())
        self.assertNotIn("niet vastgelegd",html.lower())
