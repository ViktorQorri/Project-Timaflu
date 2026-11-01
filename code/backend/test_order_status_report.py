"""AD06: order status lookup against the current sales route and repository.

The removed /reports endpoint was not required by the Timaflu case. The
authoritative status overview is /orders/status (and /orders/<id>/status).
"""
from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch
from app import create_app
from repositories.sales_case_repository import SalesCaseRepository

class Cursor:
    def __init__(self,rows):
        self.rows=rows
        self.query=None
        self.params=None
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,query,params): self.query,self.params=query,params
    def fetchall(self): return self.rows

class Connection:
    def __init__(self,rows): self.cur=Cursor(rows)
    def cursor(self,dictionary=False):
        assert dictionary
        return self.cur

class OrderStatusLookupTests(TestCase):
    def setUp(self):
        self.rows=[dict(bestelling_id=1,status_naam="wordt verzameld",
                        bedrijfsnaam="Apotheek A",
                        besteld_op=datetime(2026,10,30,10,0),
                        gewenste_leverdatum=date(2026,10,31),
                        dagdeel="ochtend",spoed=False,afleveradres="Breda")]
    def test_repository_reads_actual_order_status_without_overwriting(self):
        connection=Connection(self.rows)
        rows=SalesCaseRepository(connection).order_statuses()
        self.assertEqual(rows,self.rows)
        self.assertIn("FROM Bestelling", connection.cur.query)
        self.assertIn("ORDER BY b.besteld_op DESC", connection.cur.query)
        self.assertEqual(connection.cur.params,(None,None))
    def test_repository_filters_customer(self):
        connection=Connection([])
        self.assertEqual(SalesCaseRepository(connection).order_statuses(7),[])
        self.assertEqual(connection.cur.params,(7,7))
    def test_invalid_customer_id_is_rejected(self):
        app=create_app()
        app.testing=True
        with app.test_client() as client:
            for value in ("abc","-2","0"):
                with self.subTest(value=value):
                    self.assertEqual(client.get("/orders/status?customer_id="+value).status_code,400)
    def test_current_status_page_displays_saved_order(self):
        app=create_app()
        app.testing=True
        with patch("routes.sales.get_connection",return_value=Connection(self.rows)):
            with app.test_client() as client:
                response=client.get("/orders/status?customer_id=7")
        self.assertEqual(response.status_code,200)
        self.assertIn(b"Apotheek A",response.data)
        self.assertIn(b"wordt verzameld",response.data.lower())
