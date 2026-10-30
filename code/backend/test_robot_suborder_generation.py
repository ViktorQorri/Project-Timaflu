"""Repository transaction tests for allocating robot sub-orders (issue #16)."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, NotFoundError
from repositories.robot_order_repository import RobotOrderRepository
from services.robot_order_service import RobotOrderService


class SplitCursor:
    def __init__(self, amount=6, assigned_count=0, free_a=4, free_b=2):
        self.amount = amount
        self.assigned_count = assigned_count
        self.free_a = free_a
        self.free_b = free_b
        self.last = None
        self.commands = []
        self.lastrowid = None
        self.next_id = 40

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parameters):
        self.commands.append((sql, parameters))
        statement = " ".join(sql.split())
        if "FROM Bestelling WHERE bestelling_id" in statement:
            self.last = "order"
        elif "assigned_count FROM Deelorder" in statement:
            self.last = "assigned"
        elif "FROM Voorraadreservering" in statement:
            self.last = "reservation"
        elif "FROM Product WHERE product_id" in statement:
            self.last = "product"
        elif "FROM Magazijnlocatie" in statement:
            self.last = "aisles"
        elif "INSERT INTO Deelorder (" in statement:
            self.last = "insert"
            self.lastrowid = self.next_id
            self.next_id += 1
        else:
            self.last = "other"

    def fetchone(self):
        if self.last == "order":
            return {"bestelling_id": 30}
        if self.last == "assigned":
            return {"assigned_count": self.assigned_count}
        if self.last == "product":
            return {"product_id": 7}
        raise AssertionError(self.last)

    def fetchall(self):
        if self.last == "reservation":
            return [{"product_id": 7, "aantal": self.amount}]
        if self.last == "aisles":
            return [
                {"robot_id": 1, "gang": "A", "physical_stock": 5,
                 "already_assigned": 5 - self.free_a},
                {"robot_id": 2, "gang": "B", "physical_stock": 2,
                 "already_assigned": 2 - self.free_b},
            ]
        raise AssertionError(self.last)


class SplitConnection:
    def __init__(self, **settings):
        self.cursor_instance = SplitCursor(**settings)
        self.committed = 0
        self.rolled_back = 0

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cursor_instance

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


class RobotSplitTests(TestCase):
    def test_split_by_robot_aisle_from_reserved_stock(self):
        connection = SplitConnection()
        result = RobotOrderRepository(connection).generate(30)
        self.assertEqual(len(result), 2)
        self.assertEqual([x["robot_id"] for x in result], [1, 2])
        self.assertEqual([x["lines"][0]["aantal"] for x in result], [4, 2])
        self.assertEqual(connection.committed, 1)
        self.assertEqual(connection.rolled_back, 0)
        self.assertTrue(any("FOR UPDATE" in command
                            for command, _ in connection.cursor_instance.commands))
        self.assertEqual(sum("INSERT INTO Deelorder (" in sql
                             for sql, _ in connection.cursor_instance.commands), 2)

    def test_idempotency_prevents_duplicate_generation(self):
        connection = SplitConnection(assigned_count=1)
        with self.assertRaises(ConflictError):
            RobotOrderRepository(connection).generate(30)
        self.assertEqual(connection.committed, 0)
        self.assertEqual(connection.rolled_back, 1)

    def test_rejects_insufficient_allocatable_stock(self):
        connection = SplitConnection(amount=7)
        with self.assertRaises(ConflictError):
            RobotOrderRepository(connection).generate(30)
        self.assertEqual(connection.committed, 0)
        self.assertEqual(connection.rolled_back, 1)
        self.assertFalse(any("INSERT INTO Deelorder (" in sql
                             for sql, _ in connection.cursor_instance.commands))

    def test_dispatch_endpoint_returns_created_suborders(self):
        class Service:
            def generate_suborders(self, order_id):
                assert order_id == 30
                return [{"robot_id": 1, "suborder_id": 40, "lines": []}]
        app = create_app()
        app.config.update(TESTING=True)
        with patch("routes.api._robot_service", return_value=Service()):
            with app.test_client() as client:
                response = client.post("/api/orders/30/suborders")
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json["suborders"][0]["robot_id"], 1)
