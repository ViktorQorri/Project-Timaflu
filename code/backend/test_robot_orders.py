"""Robot dispatch tests for issue #16, using fake repositories."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError, NotFoundError
from services.robot_order_service import RobotOrderService
from repositories.robot_order_repository import RobotOrderRepository


class FakeRobotRepository:
    def __init__(self):
        self.completed = []

    def robot_for_aisle(self, ident, aisle):
        return {"robot_id": 1, "gang": "A"} if (ident, aisle) == (1, "A") else None

    def next_suborder(self, ident):
        return {"deelorder_id": 20, "bestelling_id": 30}

    def suborder_lines(self, ident):
        return [{"product_id": 7, "productnaam": "Medicijn", "aantal": 3}]

    def complete(self, ident, suborder_id):
        self.completed.append((ident, suborder_id))
        return {"deelorder_id": suborder_id, "afgerond": True}


class FakeCursor:
    def __init__(self, exists=True, bins=1, lines=1):
        self.exists = exists
        self.bins = bins
        self.lines = lines
        self.queries = []
        self.current_query = ""
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parameters):
        self.queries.append((sql, parameters))
        self.current_query = " ".join(sql.split())

    def fetchone(self):
        if "FROM Deelorder AS d" in self.current_query:
            return ({"deelorder_id": 20, "bestelling_id": 30,
                     "gang": "A", "afgerond": False} if self.exists else None)
        if "bin_count" in self.current_query:
            return {"bin_count": self.bins}
        if "FROM Product WHERE" in self.current_query:
            return {"product_id": 7}
        if "FROM Voorraadreservering" in self.current_query:
            return {"aantal": 3}
        raise AssertionError(self.current_query)

    def fetchall(self):
        if "FROM Deelorderregel" in self.current_query:
            return ([{"product_id": 7, "aantal": 3}] if self.lines else [])
        if "FROM Magazijnlocatie" in self.current_query:
            return [{"schapnummer": 4, "aantal": 3}]
        raise AssertionError(self.current_query)


class FakeConnection:
    def __init__(self, exists=True, bins=1, lines=1):
        self.cursor_instance = FakeCursor(exists, bins, lines)
        self.committed = 0
        self.rolled_back = 0

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


class RobotOrderTests(TestCase):
    def setUp(self):
        self.repo = FakeRobotRepository()
        self.service = RobotOrderService(self.repo)

    def test_assignment_is_aisle_specific(self):
        result = self.service.next_order(1, "a")
        self.assertEqual(result["suborder"]["deelorder_id"], 20)
        self.assertEqual(result["lines"][0]["aantal"], 3)
        with self.assertRaises(NotFoundError):
            self.service.next_order(1, "B")
        with self.assertRaises(DomainError):
            self.service.next_order(1, "invalid")

    def test_completion_uses_correct_robot_and_suborder(self):
        self.assertEqual(self.service.complete(1, "A", 20)["afgerond"], True)
        self.assertEqual(self.repo.completed, [(1, 20)])

    def test_transactions_require_registered_bin(self):
        bad = FakeConnection(bins=0)
        from domain.errors import ConflictError
        with self.assertRaises(ConflictError):
            RobotOrderRepository(bad).complete(1, 20)
        self.assertEqual(bad.committed, 0)
        self.assertEqual(bad.rolled_back, 1)
        good = FakeConnection(bins=1)
        self.assertEqual(RobotOrderRepository(good).complete(1, 20)["afgerond"], True)
        self.assertEqual(good.committed, 1)
        statements = [sql for sql, _ in good.cursor_instance.queries]
        self.assertTrue(any("UPDATE Magazijnlocatie" in sql for sql in statements))
        self.assertTrue(any("DELETE FROM Voorraadreservering" in sql for sql in statements))
        self.assertTrue(any("SET afgerond = TRUE" in sql for sql in statements))

    def test_completion_rejects_empty_partial_order(self):
        from domain.errors import ConflictError
        connection = FakeConnection(lines=0)
        with self.assertRaises(ConflictError):
            RobotOrderRepository(connection).complete(1, 20)
        self.assertEqual(connection.committed, 0)
        self.assertEqual(connection.rolled_back, 1)

    def test_api_routes_and_validation(self):
        app = create_app()
        app.config.update(TESTING=True)
        with patch("routes.api._robot_service", return_value=self.service):
            with app.test_client() as client:
                response = client.get("/api/robots/1/next?aisle=A")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["lines"][0]["product_id"], 7)
                response = client.get("/api/robots/1/next?aisle=B")
                self.assertEqual(response.status_code, 404)
                response = client.post("/api/robots/1/complete",
                                       json={"aisle": "A", "suborder_id": 20})
                self.assertEqual(response.status_code, 200)
                response = client.post("/api/robots/1/complete", data="invalid")
                self.assertEqual(response.status_code, 400)
