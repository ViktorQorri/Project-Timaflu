"""Real MySQL test for issue #57; only isolated, disposable database.

Explicit opt-in: TIMAFLU_TEST_MYSQL=isolated, database timaflu_test.
"""
import os
from uuid import uuid4
from unittest import TestCase, skipUnless

from repositories.purchase_order_repository import PurchaseOrderRepository

@skipUnless(
    os.environ.get("TIMAFLU_TEST_MYSQL")=="isolated"
    and os.environ.get("TIMAFLU_TEST_DATABASE")in {"timaflu_test", "timaflu_fresh"},
    "Only runs against explicitly selected disposable MySQL database",
)
class PurchaseTrackingMySQLTest(TestCase):
    def test_manual_order_records_current_date_and_status_without_backdating_history(self):
        import mysql.connector

        db=mysql.connector.connect(
            host=os.environ["TIMAFLU_TEST_HOST"],
            port=int(os.environ["TIMAFLU_TEST_PORT"]),
            user=os.environ["TIMAFLU_TEST_USER"],
            password=os.environ["TIMAFLU_TEST_PASSWORD"],
            database=os.environ["TIMAFLU_TEST_DATABASE"],
        )
        try:
            suffix=uuid4().hex[:10]
            with db.cursor() as c:
                c.execute("INSERT INTO Adres(adres) VALUES (%s)", ("Teststraat "+suffix,))
                address=c.lastrowid
                c.execute("INSERT INTO Leverancier(naam,adres_id) VALUES (%s,%s)",
                          ("Testfabrikant "+suffix,address))
                supplier=c.lastrowid
                c.execute("INSERT INTO Inkoopbestelling(leverancier_id) VALUES (%s)",(supplier,))
                legacy_order=c.lastrowid
                c.execute(
                    """INSERT INTO Product (artikelnummer,bestelcode,productnaam,
                       prijs_per_grootverpakking,aantal_detailverpakkingen,
                       minimale_bestelhoeveelheid,minimumvoorraad)
                       VALUES (%s,%s,'Testmedicijn',10,1,1,5)""",
                    ("TEST-PURCH-"+suffix,"TEST-CODE-"+suffix)
                )
                product=c.lastrowid
                c.execute(
                    "INSERT INTO LeveranciersAanbod(leverancier_id,product_id,inkoopprijs)"
                    " VALUES (%s,%s,4.50)",(supplier,product))
            db.commit()
            repo=PurchaseOrderRepository(db)
            order_id=repo.create(supplier,product,3)
            rows=repo.list_recorded()
            created=next(row for row in rows if row["inkoopbestelling_id"]==order_id)
            self.assertEqual(created["status_naam"],"besteld")
            with db.cursor() as c:
                c.execute(
                    "SELECT ABS(TIMESTAMPDIFF(SECOND,besteld_op,CURRENT_TIMESTAMP)) "
                    "FROM Inkoopbestelling WHERE inkoopbestelling_id=%s", (order_id,)
                )
                self.assertLess(c.fetchone()[0], 180)
            with db.cursor() as c:
                c.execute("SELECT besteld_op,status_naam FROM Inkoopbestelling WHERE inkoopbestelling_id=%s",(legacy_order,))
                self.assertEqual(c.fetchone(),(None,None))
        finally:
            db.close()
