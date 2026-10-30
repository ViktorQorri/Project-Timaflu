"""Picking bin registration tests, without requiring a live MySQL server."""
from unittest import TestCase
from unittest.mock import patch

from mysql.connector import IntegrityError

from app import create_app
from domain.errors import ConflictError, DomainError, NotFoundError
from repositories.picking_bin_repository import PickingBinRepository
from services.picking_bin_service import PickingBinService


class FakeCursor:
    def __init__(self, values, rows, insert_error=None):
        self.values = iter(values)
        self.rows = rows
        self.insert_error = insert_error
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if self.insert_error and query.startswith("INSERT"):
            raise self.insert_error

    def fetchone(self):
        return next(self.values)

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, values=(), rows=(), insert_error=None):
        self.cur = FakeCursor(values, list(rows), insert_error)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


OPEN_SUB_ORDER = {"deelorder_id": 7, "bestelling_id": 3, "afgerond": False, "gang": "B"}
BIN_ROW = {"unieke_code": "VB-0001", "deelorder_id": 7, "bestelling_id": 3,
           "robot_id": 2, "gang": "B", "afgerond": False}


class PickingBinRepositoryTests(TestCase):
    def test_registers_unique_bin_linked_to_order_and_aisle(self):
        db = FakeConnection([OPEN_SUB_ORDER, None])
        result = PickingBinService(PickingBinRepository(db)).register(" VB-0001 ", "7", "b")
        self.assertEqual(result, {"unieke_code": "VB-0001", "deelorder_id": 7,
                                  "bestelling_id": 3, "gang": "B"})
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertIn("FOR UPDATE", db.cur.statements[0][0])
        self.assertEqual(db.cur.statements[0][1], (7,))
        self.assertEqual(db.cur.statements[1][1], ("VB-0001",))
        self.assertIn("INSERT INTO Verzamelbak", db.cur.statements[2][0])
        self.assertEqual(db.cur.statements[2][1], ("VB-0001", 7))

    def test_duplicate_bin_code_rejected_without_insert(self):
        db = FakeConnection([OPEN_SUB_ORDER, {"deelorder_id": 5}])
        with self.assertRaises(ConflictError) as raised:
            PickingBinRepository(db).register("VB-0001", 7, "B")
        self.assertIn("deelorder 5", str(raised.exception))
        self.assertEqual(db.rollbacks, 1)
        self.assertEqual(db.commits, 0)
        self.assertFalse(any("INSERT" in s for s, _ in db.cur.statements))

    def test_simultaneous_duplicate_insert_becomes_conflict(self):
        db = FakeConnection([OPEN_SUB_ORDER, None], insert_error=IntegrityError("Duplicate entry"))
        with self.assertRaises(ConflictError):
            PickingBinRepository(db).register("VB-0001", 7, "B")
        self.assertEqual(db.rollbacks, 1)
        self.assertEqual(db.commits, 0)

    def test_unknown_sub_order_rejected(self):
        db = FakeConnection([None])
        with self.assertRaises(NotFoundError):
            PickingBinRepository(db).register("VB-0001", 99, "B")
        self.assertEqual(db.rollbacks, 1)
        self.assertEqual(len(db.cur.statements), 1)

    def test_completed_sub_order_rejected(self):
        db = FakeConnection([{**OPEN_SUB_ORDER, "afgerond": True}])
        with self.assertRaises(ConflictError):
            PickingBinRepository(db).register("VB-0001", 7, "B")
        self.assertEqual(db.rollbacks, 1)
        self.assertFalse(any("INSERT" in s for s, _ in db.cur.statements))

    def test_bin_in_other_aisle_than_sub_order_rejected(self):
        db = FakeConnection([OPEN_SUB_ORDER])
        with self.assertRaises(DomainError) as raised:
            PickingBinRepository(db).register("VB-0001", 7, "C")
        self.assertIn("gang B", str(raised.exception))
        self.assertEqual(db.rollbacks, 1)
        self.assertFalse(any("INSERT" in s for s, _ in db.cur.statements))

    def test_list_joins_bins_to_order_and_robot_aisle(self):
        db = FakeConnection(rows=[BIN_ROW])
        self.assertEqual(PickingBinRepository(db).list_bins(), [BIN_ROW])
        query = db.cur.statements[0][0]
        self.assertIn("JOIN Deelorder AS d ON d.deelorder_id = v.deelorder_id", query)
        self.assertIn("JOIN Robot AS r ON r.robot_id = d.robot_id", query)


class PickingBinServiceTests(TestCase):
    def test_invalid_input_rejected_before_query(self):
        for code, sub_order, aisle in [
            ("", 7, "B"),
            ("VB 0001", 7, "B"),
            ("V" * 51, 7, "B"),
            ("VB-0001", "x", "B"),
            ("VB-0001", 0, "B"),
            ("VB-0001", None, "B"),
            ("VB-0001", 7, "Z"),
            ("VB-0001", 7, ""),
        ]:
            db = FakeConnection()
            with self.subTest(code=code, sub_order=sub_order, aisle=aisle):
                with self.assertRaises(DomainError):
                    PickingBinService(PickingBinRepository(db)).register(code, sub_order, aisle)
                self.assertEqual(db.cur.statements, [])

    def test_status_follows_sub_order(self):
        db = FakeConnection(rows=[BIN_ROW, {**BIN_ROW, "unieke_code": "VB-0002", "afgerond": True}])
        bins = PickingBinService(PickingBinRepository(db)).bins()
        self.assertEqual([b["status"] for b in bins], ["Wordt verzameld", "Deelorder afgerond"])


class PickingBinPageTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True

    def test_page_lists_bins_and_empty_state(self):
        with self.app.test_client() as client:
            with patch("routes.order_picking.get_connection", return_value=FakeConnection(rows=[BIN_ROW])):
                response = client.get("/order-picking")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"VB-0001", response.data)
                self.assertIn(b"Gang B", response.data)
                self.assertIn(b"Wordt verzameld", response.data)
            with patch("routes.order_picking.get_connection", return_value=FakeConnection()):
                response = client.get("/order-picking")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Nog geen verzamelbakken", response.data)

    def test_page_has_no_registration_form(self):
        with self.app.test_client() as client:
            with patch("routes.order_picking.get_connection", return_value=FakeConnection()):
                response = client.get("/order-picking")
                self.assertNotIn(b"<form", response.data)
                self.assertEqual(client.post("/order-picking/bins").status_code, 404)


class PickingBinApiTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True

    def post(self, db, **kwargs):
        with self.app.test_client() as client:
            with patch("routes.api.get_connection", return_value=db):
                return client.post("/api/picking-bins", **kwargs)

    def test_robot_registers_scanned_bin(self):
        db = FakeConnection([OPEN_SUB_ORDER, None])
        response = self.post(db, json={"aisle": "B", "sub_order_id": 7, "bin_code": "VB-0001"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"accepted": True, "bin_code": "VB-0001", "order_id": 3,
                                               "sub_order_id": 7, "aisle": "B"})
        self.assertEqual(db.commits, 1)

    def test_rejections_answer_json_with_matching_status(self):
        for values, message, status in [
            ([OPEN_SUB_ORDER, {"deelorder_id": 5}], {"aisle": "B", "sub_order_id": 7, "bin_code": "VB-0001"}, 409),
            ([None], {"aisle": "B", "sub_order_id": 99, "bin_code": "VB-0001"}, 404),
            ([OPEN_SUB_ORDER], {"aisle": "C", "sub_order_id": 7, "bin_code": "VB-0001"}, 400),
            ([], {"aisle": "B", "sub_order_id": 7}, 400),
        ]:
            db = FakeConnection(values)
            with self.subTest(status=status, message=message):
                response = self.post(db, json=message)
                self.assertEqual(response.status_code, status)
                self.assertIn("error", response.get_json())
                self.assertEqual(db.commits, 0)

    def test_body_that_is_not_a_json_object_is_rejected(self):
        for kwargs in [{"data": "bin_code=VB-0001"}, {"json": ["VB-0001"]}]:
            db = FakeConnection()
            with self.subTest(kwargs=kwargs):
                response = self.post(db, **kwargs)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
                self.assertEqual(db.cur.statements, [])
