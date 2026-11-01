"""Isolated real MySQL test for the case's telephone order through signed delivery."""
from datetime import date,timedelta
from decimal import Decimal
from uuid import uuid4
from pathlib import Path
import os,re,unittest,mysql.connector
from app import create_app
from repositories.weekly_invoice_repository import WeeklyInvoiceRepository
from db import get_connection
ROOT=Path(__file__).resolve().parents[2]

@unittest.skipUnless(os.getenv("TIMAFLU_TEST_ALLOW_RESET")=="isolated" and
                     os.getenv("TIMAFLU_TEST_MYSQL_HOST")=="127.0.0.1",
                     "Needs isolated localhost MySQL opt-in")
class RealOrderChainTests(unittest.TestCase):
    def setUp(self):
        self.name="timaflu_orderchain_"+uuid4().hex[:10]
        self.options=dict(host="127.0.0.1",port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
                          user="root",password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"])
        self.admin=mysql.connector.connect(**self.options)
        with self.admin.cursor() as c: c.execute("CREATE DATABASE "+self.name)
        self.admin.commit()
        self.db=mysql.connector.connect(database=self.name,**self.options)
        sql="\n".join(x for x in (ROOT/"code/database/schema.sql").read_text(encoding="utf-8").splitlines()
                      if not x.lstrip().startswith("--"))
        with self.db.cursor() as c:
            for part in sql.split(";"):
                if part.strip():c.execute(part)
            c.execute("INSERT INTO Adres(adres) VALUES('TEST: Klant Breda')")
            c.execute("""INSERT INTO Klant(bedrijfsnaam,contactpersoon,telefoonnummer,afleveradres_id,betaaladres_id)
                         VALUES('TEST Apotheek','TEST Contact','0612345678',1,1)""")
            c.execute("""INSERT INTO Product(artikelnummer,bestelcode,productnaam,prijs_per_grootverpakking,
                         aantal_detailverpakkingen,minimale_bestelhoeveelheid,minimumvoorraad)
                         VALUES('TEST-01','ORDER-TEST','TEST Medicijn',100,1,1,1)""")
            c.execute("INSERT INTO Robot(robot_id,gang) VALUES(1,'A')")
            c.execute("INSERT INTO Magazijnlocatie(gang,schapnummer,product_id,aantal) VALUES('A',1,1,5)")
            c.execute("INSERT INTO Koerier(naam,beschikbaar) VALUES('TEST Koerier',TRUE)")
        self.db.commit()
        self.app=create_app()
        self.app.config.update(TESTING=True,SECRET_KEY="test-orderchain",
            DB_HOST="127.0.0.1",DB_PORT=self.options["port"],DB_NAME=self.name,
            DB_USER="root",DB_PASSWORD=self.options["password"],TIMAFLU_ADDRESS="TEST fictief")

    def tearDown(self):
        self.db.close()
        with self.admin.cursor() as c:c.execute("DROP DATABASE "+self.name)
        self.admin.commit()
        self.admin.close()

    def scalar(self,statement):
        # End the old REPEATABLE READ snapshot before observing writes committed
        # by Flask through a separate database connection.
        self.db.rollback()
        with self.db.cursor() as c:
            c.execute(statement)
            row = c.fetchone()
            self.assertIsNotNone(row, statement)
            return row[0]

    def quote(self,client,n,shortage="skip",slot="ochtend"):
        data={"customer_id":"1","day":(date.today()+timedelta(days=1)).isoformat(),"slot":slot,
              "product_id":["1","","","","",""],"quantity":[str(n),"","","","",""],
              "shortage":[shortage]+["skip"]*5}
        return client.post("/orders/quote",data=data)

    def token(self,response):
        match=re.search(rb'name="quote_token" value="([^"]+)"',response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_signed_delivery_releases_reserved_stock_and_invoices_once(self):
        day=date.today()+timedelta(days=1)
        with self.app.test_client() as client:
            self.assertEqual(client.get("/orders/new").status_code,200)
            preview=self.quote(client,3)
            self.assertEqual(preview.status_code,200,preview.data[:300])
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Bestelling"),0)
            token=self.token(preview)
            self.assertEqual(client.post("/orders/confirm",
                data={"quote_token":token,"customer_approved":"yes"}).status_code,302)
            self.assertEqual(self.scalar("SELECT aantal FROM Voorraadreservering"),3)
            self.assertEqual(self.scalar("SELECT aantal FROM Magazijnlocatie"),5)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Deelorder"),1)
            self.assertEqual(client.post("/orders/confirm",
                data={"quote_token":token,"customer_approved":"yes"}).status_code,400)
            self.assertEqual(client.post("/api/picking-bins",
                json={"bin_code":"TEST-BIN-01","sub_order_id":1,"aisle":"A"}).status_code,200)
            result=client.post("/api/robots/1/complete",json={"aisle":"A","suborder_id":1})
            self.assertEqual(result.status_code,200,result.data[:300])
            self.assertEqual(self.scalar("SELECT aantal FROM Magazijnlocatie"),2)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Voorraadreservering"),0)
            self.assertEqual(client.post("/api/robots/1/complete",
                json={"aisle":"A","suborder_id":1}).status_code,409)
            self.assertEqual(client.get("/order-picking").status_code,200)
            self.assertEqual(client.post("/order-picking/orders/1/pack").status_code,302)
            self.assertEqual(self.scalar("SELECT aantal_geleverd FROM Leveringregel"),3)
            self.assertEqual(client.post("/order-picking/orders/1/pack").status_code,409)
            self.assertEqual(client.get("/deliveries").status_code,200)
            self.assertEqual(client.post("/deliveries/plan",
                data={"delivery_id":1,"courier_id":1,"day":day.isoformat(),
                      "time":"10:00","courier_assignment_confirmed":"yes"}).status_code,302)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Leverpoging"),1)
            self.assertEqual(client.post("/deliveries/first-attempt/delivered",
                data={"day":day.isoformat(),"delivery_id":"1","signature_confirmed":"yes"}).status_code,302)
            with self.app.app_context():
                week=day-timedelta(days=day.weekday())
                ids=WeeklyInvoiceRepository(get_connection()).issue_week(
                    week,"TEST fictief",issued_on=week+timedelta(days=7))
            self.assertEqual(len(ids),1)
            self.assertEqual(self.scalar("SELECT totaal_bedrag FROM Factuur"),Decimal("279.58"))
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Leveringregel WHERE factuur_id IS NOT NULL"),1)

    def test_shortage_needs_customer_choice_and_never_reserves_missing_stock(self):
        with self.app.test_client() as client:
            self.assertEqual(self.quote(client,8).status_code,400)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Bestelling"),0)
            preview=self.quote(client,8,"later",slot="middag")
            self.assertEqual(preview.status_code,200,preview.data[:300])
            token=self.token(preview)
            self.assertEqual(client.post("/orders/confirm",
                data={"quote_token":token,"customer_approved":"yes"}).status_code,302)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Voorraadreservering"),0)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Deelorder"),0)
            self.assertEqual(self.scalar("SELECT status_naam FROM Bestelling"),"backorder")

    def test_two_failed_visits_can_be_rescheduled_and_charge_billed_once(self):
        first = date.today()+timedelta(days=1)
        retry = first + timedelta(days=1)
        with self.app.test_client() as client:
            quote = self.quote(client, 3)
            token = self.token(quote)
            self.assertEqual(client.post("/orders/confirm",
                data={"quote_token": token, "customer_approved": "yes"}).status_code, 302)
            self.assertEqual(client.post("/api/picking-bins",
                json={"bin_code": "RETRY-BIN", "sub_order_id": 1, "aisle": "A"}).status_code, 200)
            self.assertEqual(client.post("/api/robots/1/complete",
                json={"aisle": "A", "suborder_id": 1}).status_code, 200)
            self.assertEqual(client.post("/order-picking/orders/1/pack").status_code, 302)
            self.assertEqual(client.post("/deliveries/plan",
                data={"delivery_id": 1, "courier_id": 1, "day": first.isoformat(),
                      "time": "10:00", "courier_assignment_confirmed": "yes"}).status_code, 302)
            self.assertEqual(client.post("/deliveries/second-attempt",
                data={"day": first.isoformat(), "delivery_id": 1,
                      "time": "14:00"}).status_code, 302)
            self.assertEqual(client.post("/deliveries/second-attempt/result",
                data={"day": first.isoformat(), "delivery_id": 1,
                      "outcome": "niet aanwezig"}).status_code, 302)
            followup = client.post("/deliveries/failed-followup",
                data={"day": first.isoformat(), "delivery_id": 1,
                      "requested_date": retry.isoformat(), "time_slot": "ochtend",
                      "customer_contact_confirmed": "yes",
                      "extra_cost": "10.90", "explanation": "Twee keer niet aanwezig"})
            self.assertEqual(followup.status_code, 302, followup.data[:300])
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Levering"), 2)
            self.assertEqual(self.scalar("SELECT levering_id FROM Leveringregel"), 2)
            self.assertEqual(client.post("/deliveries/plan",
                data={"delivery_id": 2, "courier_id": 1, "day": retry.isoformat(),
                      "time": "10:00", "courier_assignment_confirmed": "yes"}).status_code, 302)
            self.assertEqual(client.post("/deliveries/first-attempt/delivered",
                data={"day": retry.isoformat(), "delivery_id": 2,
                      "signature_confirmed": "yes"}).status_code, 302)
            week = retry - timedelta(days=retry.weekday())
            with self.app.app_context():
                issued = WeeklyInvoiceRepository(get_connection()).issue_week(
                    week, "TEST fictief", issued_on=week + timedelta(days=7),
                    delivery_cost_vat_percent="9")
            self.assertEqual(len(issued), 1)
            self.assertEqual(self.scalar("SELECT extra_bezorgkosten_incl_btw FROM Factuur"), Decimal("10.90"))
            self.assertEqual(self.scalar("SELECT extra_bezorgkosten_excl_btw FROM Factuur"), Decimal("10.00"))
            self.assertEqual(self.scalar("SELECT extra_bezorgkosten_btw FROM Factuur"), Decimal("0.90"))
            self.assertEqual(self.scalar("SELECT totaal_bedrag FROM Factuur"), Decimal("290.48"))
            self.assertEqual(self.scalar("SELECT extra_bezorgkosten_factuur_id FROM Bestelling"), issued[0])
            with self.app.app_context():
                again = WeeklyInvoiceRepository(get_connection()).issue_week(
                    week, "TEST fictief", issued_on=week + timedelta(days=8),
                    delivery_cost_vat_percent="9")
            self.assertEqual(again, [])
            self.assertEqual(client.get(f"/invoices/issued/{issued[0]}").status_code, 200)

    def test_deactivated_customer_cannot_approve_new_order(self):
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE Klant SET actief=FALSE WHERE klant_id=1")
        self.db.commit()
        with self.app.test_client() as client:
            page = client.get("/orders/new")
            self.assertEqual(page.status_code, 200)
            self.assertNotIn(b"TEST Apotheek", page.data)
            self.assertEqual(self.quote(client, 2).status_code, 400)
            self.assertEqual(self.scalar("SELECT COUNT(*) FROM Bestelling"), 0)
