"""Isolated unit tests for reservation transaction safety."""
from unittest import TestCase
from domain.errors import ConflictError, DomainError, NotFoundError
from repositories.reservation_repository import ReservationRepository
from services.reservation_service import ReservationService


class FakeCursor:
    def __init__(self, values):
        self.values = iter(values)
        self.statements = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.statements.append((query, params))

    def fetchone(self):
        return next(self.values)


class FakeConnection:
    def __init__(self, values):
        self.cur = FakeCursor(values)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class ReservationTests(TestCase):
    def test_reserves_only_when_available(self):
        db = FakeConnection([(4,), (3,), None, (10,), (5,)])
        count = ReservationService(ReservationRepository(db)).reserve_confirmed_line(1, 4)
        self.assertEqual(count, 3)
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertIn("FOR UPDATE", db.cur.statements[0][0])
        self.assertIn("INSERT INTO Voorraadreservering", db.cur.statements[-1][0])

    def test_shortage_rolls_back_without_insert(self):
        db = FakeConnection([(4,), (7,), None, (10,), (5,)])
        with self.assertRaises(ConflictError):
            ReservationService(ReservationRepository(db)).reserve_confirmed_line(1, 4)
        self.assertEqual(db.rollbacks, 1)
        self.assertFalse(any("INSERT INTO" in s for s, _ in db.cur.statements))

    def test_duplicate_reservation_rejected(self):
        db = FakeConnection([(4,), (2,), (2,)])
        with self.assertRaises(ConflictError):
            ReservationRepository(db).reserve_existing_line(1, 4)
        self.assertEqual(db.commits, 0)

    def test_releasing_reservation(self):
        db = FakeConnection([(4,)])
        self.assertTrue(ReservationService(ReservationRepository(db)).release_line(1, 4))
        self.assertEqual(db.commits, 1)
        self.assertIn("DELETE FROM Voorraadreservering", db.cur.statements[1][0])

    def test_invalid_ids_rejected_before_query(self):
        db = FakeConnection([])
        with self.assertRaises(DomainError):
            ReservationService(ReservationRepository(db)).reserve_confirmed_line("x", -1)
        self.assertEqual(db.cur.statements, [])

    def test_missing_product_rolled_back(self):
        db = FakeConnection([None])
        with self.assertRaises(NotFoundError):
            ReservationRepository(db).reserve_existing_line(2, 4)
        self.assertEqual(db.rollbacks, 1)
