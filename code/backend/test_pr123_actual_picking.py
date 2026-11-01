"""Casus AD11: robots report actual collected quantities, not assumed quantities."""
from unittest import TestCase

from domain.errors import ConflictError
from repositories.robot_order_repository import RobotOrderRepository
from test_robot_orders import FakeConnection


class ActualRobotPickingTests(TestCase):
    def test_partial_picking_releases_all_assigned_reservations(self):
        connection = FakeConnection()
        saved = RobotOrderRepository(connection).complete(1, 20, {7: 1})
        self.assertTrue(saved["afgerond"])
        self.assertTrue(saved["backorder"])
        self.assertEqual(connection.committed, 1)
        sql = connection.cursor_instance.queries
        self.assertIn((1, "A", 4, 1), [params for statement, params in sql
                                         if "UPDATE Magazijnlocatie" in statement])
        self.assertIn((1, 20, 7), [params for statement, params in sql
                                   if "UPDATE Deelorderregel" in statement])
        self.assertTrue(any("afnemen_bij_tekort = TRUE" in stmt for stmt, _ in sql))
        self.assertTrue(any("status_naam = 'backorder'" in stmt for stmt, _ in sql))
        self.assertTrue(any("DELETE FROM Voorraadreservering" in stmt for stmt, _ in sql))

    def test_zero_collected_keeps_no_fictitious_delivery_line(self):
        connection = FakeConnection()
        saved = RobotOrderRepository(connection).complete(1, 20, {7: 0})
        self.assertTrue(saved["backorder"])
        sql = connection.cursor_instance.queries
        self.assertFalse(any("UPDATE Magazijnlocatie" in stmt for stmt, _ in sql))
        self.assertTrue(any("DELETE FROM Deelorderregel" in stmt for stmt, _ in sql))
        self.assertEqual(connection.committed, 1)

    def test_more_collected_than_assigned_is_rejected(self):
        connection = FakeConnection()
        with self.assertRaisesRegex(ConflictError, "groter"):
            RobotOrderRepository(connection).complete(1, 20, {7: 4})
        self.assertEqual(connection.committed, 0)
        self.assertEqual(connection.rolled_back, 1)

    def test_missing_or_unassigned_product_is_rejected(self):
        for collected in ({}, {8: 3}, {7: 3, 8: 2}):
            with self.subTest(collected=collected):
                connection = FakeConnection()
                with self.assertRaises(ConflictError):
                    RobotOrderRepository(connection).complete(1, 20, collected)
                self.assertEqual(connection.committed, 0)
                self.assertEqual(connection.rolled_back, 1)
