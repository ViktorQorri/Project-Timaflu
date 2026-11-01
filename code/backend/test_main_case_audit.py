"""Independent case regressions for integrated main, based on the official Timaflu documents."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from domain.business import Order
from services.product_service import ProductService
from test_product_catalog import FakeProductRepository, FakeSupplierRepository, form_data

ROOT = Path(__file__).resolve().parents[2]


class MainCaseAuditTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="case-audit")

    def test_supplier_actions_exist_once_without_invalid_get_links(self):
        source = (ROOT / "code/frontend/templates/suppliers.html").read_text(encoding="utf-8")
        self.assertEqual(source.count("url_for('purchasing.remove_offer')"), 1)
        self.assertEqual(source.count("url_for('purchasing.remove_product',"), 1)
        self.assertEqual(source.count("url_for('purchasing.remove_product_from_reorder_list')"), 1)
        self.assertNotIn("url_for('purchasing.manufacturer_offer_remove'", source)
        self.assertNotIn(chr(96)+"n", source)

    def test_acquisition_refusal_is_accessible_in_the_real_form(self):
        prospect = dict(
            potentiele_klant_id=3, bedrijfsnaam="TEST Apotheek", contactpersoon="TEST Contact",
            contactgegevens="0612345678", adres="Testadres", bezoekdatum=date(2026, 9, 1),
            klant_id=None,
        )
        class FakeRepo:
            def __init__(self, connection):
                pass
            def prospect_followups(self, cutoff):
                return [prospect]
        with patch("routes.acquisition.get_connection", return_value=object()):
            with patch("routes.acquisition.AssessedRepository", FakeRepo):
                response = self.app.test_client().get("/acquisition")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'action="/acquisition/decline"', response.data)
        self.assertIn(b'name="declined"', response.data)
        self.assertIn(b'Opvolging afsluiten', response.data)

    def test_catalog_requires_explicit_director_approval_even_without_browser(self):
        service = ProductService(FakeProductRepository(), FakeSupplierRepository())
        with self.assertRaisesRegex(DomainError, "directie"):
            service.add_product(form_data(director_approved=""))
        with self.assertRaisesRegex(DomainError, "directie"):
            service.add_product(form_data(director_approved="no"))
        self.assertIn(
            'name="director_approved"',
            (ROOT / "code/frontend/templates/product_form.html").read_text(encoding="utf-8")
        )

    def test_invalid_delivery_inputs_return_four_hundred_not_server_error(self):
        with self.app.test_client() as client:
            requests = [
                client.get("/deliveries?day=wrong"),
                client.post("/deliveries/second-attempt", data={}),
                client.post("/deliveries/second-attempt/result", data={"day": "wrong"}),
                client.post("/deliveries/failed-followup", data={"delivery_id": "oops"}),
            ]
        self.assertEqual([r.status_code for r in requests], [400, 400, 400, 400])

    def test_negative_or_non_numeric_sales_discount_is_rejected(self):
        class FakeAssessed:
            def __init__(self, connection):
                pass
            def customer_revenue(self, customer_id, year):
                return {"bedrijfsnaam": "TEST", "klantadres": "TEST"}, Decimal("0")
            def customer_order_count(self, customer_id):
                return 0
        with patch("routes.sales.get_connection", return_value=object()):
            with patch("routes.sales.AssessedRepository", FakeAssessed):
                with self.app.test_client() as client:
                    for amount in ("-1", "not-a-number", "NaN", "Infinity"):
                        response = client.post("/orders/calculate-discount",
                            data={"customer_id": "1", "subtotal": amount})
                        self.assertEqual(response.status_code, 400, amount)

    def test_debt_collection_requires_explicit_customer_refusal(self):
        class FakeRepo:
            calls = []
            def __init__(self, connection):
                pass
            def invoice_for_customer(self, customer_id):
                return [dict(factuur_id=4, totaal_bedrag=Decimal("50"))]
            def record_payment_action(self, invoice_id, action, today):
                self.calls.append((invoice_id, action))
        FakeRepo.calls=[]
        with patch("routes.administration.get_connection", return_value=object()):
            with patch("routes.administration.AssessedRepository", FakeRepo):
                with self.app.test_client() as client:
                    args=dict(invoice_id="4", customer_id="2", action="payment_plan_rejected")
                    self.assertEqual(client.post("/invoices/actions", data=args).status_code, 400)
                    self.assertEqual(FakeRepo.calls, [])
                    args["offer_refused_confirmed"]="yes"
                    self.assertEqual(client.post("/invoices/actions", data=args).status_code, 302)
        self.assertEqual(FakeRepo.calls, [(4, "payment_plan_rejected")])

    def test_customer_and_order_status_are_real_database_backed(self):
        from repositories.sales_case_repository import SalesCaseRepository
        class Cursor:
            def __init__(self):
                self.queries=[]
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, sql, params):
                self.queries.append((" ".join(sql.split()), params))
            def fetchall(self):
                return []
        class DB:
            def __init__(self):
                self.c=Cursor()
            def cursor(self, dictionary=False):
                assert dictionary
                return self.c
        db=DB()
        repo=SalesCaseRepository(db)
        self.assertEqual(repo.customers("TEST"),[])
        self.assertEqual(db.c.queries[-1][1],("TEST","%TEST%"))
        self.assertIn("JOIN Adres",db.c.queries[-1][0])
        self.assertEqual(repo.order_statuses(3),[])
        self.assertEqual(db.c.queries[-1][1],(3,3))
        self.assertIn("JOIN Bestelling",db.c.queries[-1][0].replace("FROM Bestelling","JOIN Bestelling"))
        with self.assertRaises(DomainError):
            repo.customers("x"*101)

    def test_issued_invoice_table_is_keyboard_scrollable_on_mobile(self):
        html = (ROOT / "code/frontend/templates/issued_invoice.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('class="stock-dashboard__table-wrap"', html)
        self.assertIn('aria-label="Factuurregels"', html)
        self.assertIn('tabindex="0"', html)
        self.assertIn('class="stock-dashboard__table"', html)

    def test_discount_threshold_uses_confirmed_original_order(self):
        discount = Order("218", 0, True, orderTotal="654").calculateTotalAmount()
        self.assertEqual(discount["order_discount"], Decimal("10.90"))
        self.assertEqual(discount["first_order_discount"], Decimal("20.71"))
