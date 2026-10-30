"""Entering a telephone order (AD05) without a live MySQL server."""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, DomainError, NotFoundError
from repositories.order_repository import OrderRepository
from services.discount_service import DiscountService
from services.order_service import OrderService

TODAY = date(2026, 10, 30)
CUSTOMER = {"klant_id": 7, "bedrijfsnaam": "Apotheek De Brug"}
PRODUCTS = {
    1: {"product_id": 1, "artikelnummer": "TIM-1", "productnaam": "Medicine A",
        "prijs_per_grootverpakking": Decimal("100.00")},
    2: {"product_id": 2, "artikelnummer": "TIM-2", "productnaam": "Medicine B",
        "prijs_per_grootverpakking": Decimal("20.00")},
}


class FakeDiscountRepository:
    def list_customers(self):
        return [CUSTOMER]

    def list_products(self):
        return list(PRODUCTS.values())

    def find_customer(self, customer_id):
        return CUSTOMER if customer_id == CUSTOMER["klant_id"] else None

    def find_product(self, product_id):
        return PRODUCTS.get(product_id)

    def count_previous_orders(self, customer_id):
        return 2

    def sum_purchases(self, customer_id, year):
        return Decimal("12000.00")


class FakeOrderRepository:
    def __init__(self, stock=None, blocked=False):
        self.stock = stock or {1: 50, 2: 50}
        self.blocked = blocked
        self.saved = []

    def is_customer_blocked(self, customer_id):
        return self.blocked

    def available_stock(self, product_id):
        return self.stock[product_id]

    def save_order(self, customer_id, lines, delivery_date, part_of_day, urgent):
        self.saved.append((customer_id, lines, delivery_date, part_of_day, urgent))
        return {"order_id": 15, "first_order": False,
                "backorders": [line["product_id"] for line in lines if line["backorder"]]}


def order_service(repository=None):
    return OrderService(repository or FakeOrderRepository(), DiscountService(FakeDiscountRepository()))


class OrderServiceTests(TestCase):
    def test_prepare_shows_stock_per_line_and_total(self):
        calculation = order_service(FakeOrderRepository({1: 10, 2: 3})).prepare("7", [("1", "10"), ("2", "5")])
        self.assertEqual([(line["available"], line["short"]) for line in calculation["lines"]], [(10, False), (3, True)])
        self.assertFalse(calculation["can_save"])
        self.assertEqual(calculation["total_amount"], Decimal("940.50"))

    def test_accepted_backorder_allows_saving(self):
        calculation = order_service(FakeOrderRepository({1: 10, 2: 3})).prepare("7", [("1", "10"), ("2", "5")], ["2"])
        self.assertTrue(calculation["lines"][1]["backorder"])
        self.assertTrue(calculation["can_save"])

    def test_blocked_customer_cannot_order(self):
        with self.assertRaises(ConflictError) as raised:
            order_service(FakeOrderRepository(blocked=True)).prepare("7", [("1", "1")])
        self.assertIn("incassobureau", str(raised.exception))

    def test_place_saves_lines_and_delivery_moment(self):
        repository = FakeOrderRepository({1: 10, 2: 3})
        saved = order_service(repository).place("7", [("1", "10"), ("2", "5")], ["2"], "2026-11-02", "ochtend", False, TODAY)
        self.assertEqual(saved["order_id"], 15)
        self.assertEqual(saved["total_amount"], Decimal("940.50"))
        customer_id, lines, delivery_date, part_of_day, urgent = repository.saved[0]
        self.assertEqual(customer_id, 7)
        self.assertEqual([(line["product_id"], line["quantity"], line["backorder"]) for line in lines],
                         [(1, 10, False), (2, 5, True)])
        self.assertEqual((delivery_date, part_of_day, urgent), (date(2026, 11, 2), "ochtend", False))

    def test_only_urgent_order_is_delivered_today(self):
        with self.assertRaises(DomainError):
            order_service().place("7", [("1", "1")], [], "2026-10-30", "middag", False, TODAY)
        repository = FakeOrderRepository()
        order_service(repository).place("7", [("1", "1")], [], "2026-10-30", "middag", True, TODAY)
        self.assertEqual(repository.saved[0][2], TODAY)

    def test_invalid_order_is_not_saved(self):
        for lines, backorders, delivery_date, part_of_day in [
            ([("2", "5")], [], "2026-11-02", "ochtend"),
            ([("1", "1")], [], "2026-10-29", "ochtend"),
            ([("1", "1")], [], "", "ochtend"),
            ([("1", "1")], [], "2-11-2026", "ochtend"),
            ([("1", "1")], [], "2026-11-02", "avond"),
        ]:
            repository = FakeOrderRepository({1: 10, 2: 3})
            with self.subTest(lines=lines, delivery_date=delivery_date, part_of_day=part_of_day):
                with self.assertRaises(DomainError):
                    order_service(repository).place("7", lines, backorders, delivery_date, part_of_day, False, TODAY)
                self.assertEqual(repository.saved, [])


class Cursor:
    """Answers each query by a word in its SQL, like the tables in schema.sql."""

    def __init__(self, stock, previous_orders, blocked, customer):
        self.stock = stock
        self.previous_orders = previous_orders
        self.blocked = blocked
        self.customer = customer
        self.statements = []
        self.lastrowid = 15

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.statements.append((query, params))

    def fetchone(self):
        query, params = self.statements[-1]
        if "aantal_facturen" in query:
            return {"aantal_facturen": 1 if self.blocked else 0}
        if "aantal_bestellingen" in query:
            return {"aantal_bestellingen": self.previous_orders}
        if "beschikbaar" in query:
            return {"beschikbaar": self.stock[params[0]]}
        if "FROM Klant" in query:
            return self.customer
        if "FROM Product" in query:
            return PRODUCTS.get(params[0])
        raise AssertionError(query)


class Connection:
    def __init__(self, stock=None, previous_orders=0, blocked=False,
                 customer={"klant_id": 7, "afleveradres_id": 3, "betaaladres_id": 4}):
        self.cur = Cursor(stock or {1: 50, 2: 50}, previous_orders, blocked, customer)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def line(product_id, quantity, backorder=False):
    return {"product_id": product_id, "productnaam": PRODUCTS[product_id]["productnaam"],
            "quantity": quantity, "backorder": backorder}


def inserts(connection, table):
    return [params for query, params in connection.cur.statements if f"INSERT INTO {table} " in query]


class OrderRepositoryTests(TestCase):
    def test_saves_order_lines_and_reservations_in_one_transaction(self):
        db = Connection()
        saved = OrderRepository(db).save_order(7, [line(2, 5), line(1, 10)], date(2026, 11, 2), "ochtend", False)
        self.assertEqual(saved, {"order_id": 15, "first_order": True, "backorders": []})
        self.assertIn("FOR UPDATE", db.cur.statements[0][0])
        locked = [params for query, params in db.cur.statements if "FROM Product" in query]
        self.assertEqual(locked, [(1,), (2,)])
        self.assertEqual(inserts(db, "Bestelling"), [(7, 3, 4, date(2026, 11, 2), "ochtend", False, None, True)])
        self.assertEqual(inserts(db, "Bestelregel"), [(15, 1, 10, Decimal("100.00"), None),
                                                      (15, 2, 5, Decimal("20.00"), None)])
        self.assertEqual(inserts(db, "Voorraadreservering"), [(15, 1, 10), (15, 2, 5)])
        self.assertEqual((db.commits, db.rollbacks), (1, 0))

    def test_accepted_shortage_is_saved_as_backorder_without_reservation(self):
        db = Connection(stock={1: 50, 2: 3}, previous_orders=4)
        saved = OrderRepository(db).save_order(7, [line(1, 10), line(2, 5, backorder=True)], date(2026, 11, 2), "middag", True)
        self.assertEqual(saved, {"order_id": 15, "first_order": False, "backorders": [2]})
        self.assertEqual(inserts(db, "Bestelling")[0][5:], (True, "backorder", False))
        self.assertEqual(inserts(db, "Bestelregel")[1], (15, 2, 5, Decimal("20.00"), True))
        self.assertEqual(inserts(db, "Voorraadreservering"), [(15, 1, 10)])

    def test_changed_stock_rejects_whole_order(self):
        db = Connection(stock={1: 50, 2: 3})
        with self.assertRaises(ConflictError) as raised:
            OrderRepository(db).save_order(7, [line(1, 10), line(2, 5)], date(2026, 11, 2), "ochtend", False)
        self.assertIn("nog 3 van Medicine B", str(raised.exception))
        self.assertEqual((db.commits, db.rollbacks), (0, 1))
        self.assertEqual(inserts(db, "Bestelling"), [])

    def test_blocked_or_unknown_customer_rejected(self):
        db = Connection(blocked=True)
        with self.assertRaises(ConflictError):
            OrderRepository(db).save_order(7, [line(1, 1)], date(2026, 11, 2), "ochtend", False)
        self.assertEqual(db.rollbacks, 1)
        db = Connection(customer=None)
        with self.assertRaises(NotFoundError):
            OrderRepository(db).save_order(8, [line(1, 1)], date(2026, 11, 2), "ochtend", False)
        self.assertEqual(db.rollbacks, 1)

    def test_checks_use_placeholders(self):
        db = Connection(stock={1: 12}, blocked=True)
        repository = OrderRepository(db)
        self.assertTrue(repository.is_customer_blocked(7))
        self.assertEqual(db.cur.statements[-1][1], (7,))
        self.assertEqual(repository.available_stock(1), 12)
        self.assertEqual(db.cur.statements[-1][1], (1, 1))
        self.assertEqual(db.commits, 0)


class OrderPageTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True

    def request(self, repository, method, url, **kwargs):
        with self.app.test_client() as client:
            with patch("routes.sales._order_service", return_value=order_service(repository)):
                return getattr(client, method)(url, **kwargs)

    def test_page_shows_stock_discounts_and_backorder_choice(self):
        response = self.request(FakeOrderRepository({1: 10, 2: 3}), "get",
                                "/orders/new?customer_id=7&product_id=1&quantity=10&product_id=2&quantity=5")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Nieuwe order", page)
        self.assertIn("Tekort", page)
        self.assertIn('name="backorder" value="2"', page)
        self.assertIn("Klantenkorting (10% over € 1.045,00)", page)
        self.assertIn("Order opslaan", page)

    def test_saved_order_redirects_with_order_number(self):
        repository = FakeOrderRepository()
        with self.app.test_client() as client:
            with patch("routes.sales._order_service", return_value=order_service(repository)):
                response = client.post("/orders/new", data={
                    "customer_id": "7", "product_id": ["1", ""], "quantity": ["2", ""],
                    "delivery_date": "2099-01-05", "part_of_day": "middag",
                })
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].endswith("/orders/new"))
                page = client.get(response.headers["Location"]).get_data(as_text=True)
        self.assertIn("Order 15 is opgeslagen. Levering op 05-01-2099 in de middag.", page)
        self.assertEqual(len(repository.saved), 1)

    def test_rejected_order_keeps_input(self):
        repository = FakeOrderRepository()
        response = self.request(repository, "post", "/orders/new", data={
            "customer_id": "7", "product_id": "1", "quantity": "2",
            "delivery_date": "2000-01-05", "part_of_day": "middag", "urgent": "1",
        })
        self.assertEqual(response.status_code, 400)
        page = response.get_data(as_text=True)
        self.assertIn("De leverdatum ligt in het verleden.", page)
        self.assertIn('value="2000-01-05"', page)
        self.assertIn('name="urgent" value="1" checked', page)
        self.assertEqual(repository.saved, [])

    def test_blocked_customer_gets_conflict(self):
        response = self.request(FakeOrderRepository(blocked=True), "get", "/orders/new?customer_id=7&product_id=1&quantity=1")
        self.assertEqual(response.status_code, 409)
        self.assertIn("incassobureau", response.get_data(as_text=True))
