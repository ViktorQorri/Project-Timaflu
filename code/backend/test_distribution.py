"""Tests for grouping picking bins and releasing packed customer orders."""

from datetime import date, time
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.distribution_repository import DistributionRepository
from services.distribution_service import DistributionService


class FakeCursor:
    def __init__(self, one_rows=(), all_rows=()):
        self.one_rows = list(one_rows)
        self.all_rows = list(all_rows)
        self.statements = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        return self.one_rows.pop(0) if self.one_rows else None

    def fetchall(self):
        return self.all_rows.pop(0) if self.all_rows else []


class FakeConnection:
    def __init__(self, one_rows=(), all_rows=()):
        self.cursor_instance = FakeCursor(one_rows, all_rows)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def distribution_row(order_id, sub_order_id, bin_code, aisle, complete):
    return {
        "bestelling_id": order_id,
        "status_naam": "wordt verzameld",
        "spoed": False,
        "gewenste_leverdatum": "2026-11-01",
        "dagdeel": "ochtend",
        "aantal_verhuisdozen": 0,
        "bedrijfsnaam": f"Apotheek {order_id}",
        "afleveradres": "Voorbeeldstraat 1",
        "deelorder_id": sub_order_id,
        "afgerond": complete,
        "unieke_code": bin_code,
        "gang": aisle,
    }


class DistributionRepositoryTests(TestCase):
    def test_list_query_reads_bins_grouped_by_order(self):
        rows = [distribution_row(3, 5, "VB-1", "A", True)]
        connection = FakeConnection(all_rows=[rows])

        result = DistributionRepository(connection).list_orders_with_bins()

        self.assertEqual(result, rows)
        query = connection.cursor_instance.statements[0][0]
        self.assertIn("JOIN Deelorder", query)
        self.assertIn("Verzamelbak", query)
        self.assertIn("ORDER BY b.bestelling_id", query)
        self.assertEqual(connection.cursor_instance.statements[0][1], None)

    def test_pack_order_records_box_count_after_all_suborders_finish(self):
        connection = FakeConnection(
            one_rows=[
                {"bestelling_id": 3, "status_naam": "wordt verzameld"},
                {"unieke_code": "VB-1"},
            ],
            all_rows=[[{"deelorder_id": 5, "afgerond": True}]],
        )

        DistributionRepository(connection).pack_order(3, 2)

        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        update, params = connection.cursor_instance.statements[-1]
        self.assertIn("aantal_verhuisdozen = %s", update)
        self.assertEqual(params, (2, 3))

    def test_pack_order_rejects_incomplete_suborders(self):
        connection = FakeConnection(
            one_rows=[{"bestelling_id": 3, "status_naam": "wordt verzameld"}],
            all_rows=[[{"deelorder_id": 5, "afgerond": False}]],
        )

        with self.assertRaises(ConflictError):
            DistributionRepository(connection).pack_order(3, 2)

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(len(connection.cursor_instance.statements), 2)

    def test_release_order_requires_a_packed_order(self):
        connection = FakeConnection(
            one_rows=[{"status_naam": "wordt verzameld", "aantal_verhuisdozen": 0}]
        )

        with self.assertRaises(ConflictError):
            DistributionRepository(connection).release_order(3)

        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(len(connection.cursor_instance.statements), 1)

    def test_release_packed_order_sets_shipped_status(self):
        connection = FakeConnection(
            one_rows=[{"status_naam": "ingepakt", "aantal_verhuisdozen": 2}]
        )

        DistributionRepository(connection).release_order(3)

        self.assertEqual(connection.commits, 1)
        update, params = connection.cursor_instance.statements[-1]
        self.assertIn("status_naam = 'verstuurd'", update)
        self.assertEqual(params, (3,))


class DistributionServiceTests(TestCase):
    def test_orders_are_grouped_and_packability_is_derived(self):
        rows = [
            distribution_row(3, 5, "VB-1", "A", True),
            distribution_row(3, 5, "VB-2", "A", True),
            distribution_row(4, 6, "VB-3", "B", False),
        ]
        repository = type(
            "Repository",
            (),
            {
                "list_orders_with_bins": lambda _: rows,
                "list_order_lines": lambda _, order_id: [{"bestelling_id": order_id}],
            },
        )()

        orders = DistributionService(repository).orders_with_bins()

        self.assertEqual(len(orders), 2)
        self.assertEqual(len(orders[0]["bakken"]), 2)
        self.assertEqual(orders[0]["bestelregels"], [{"bestelling_id": 3}])
        self.assertTrue(orders[0]["kan_verpakken"])
        self.assertFalse(orders[1]["kan_verpakken"])

    def test_invalid_box_count_is_rejected_before_repository_call(self):
        class NoWriteRepository:
            def pack_order(self, *_):
                raise AssertionError("invalid input must not reach the repository")

        with self.assertRaises(DomainError):
            DistributionService(NoWriteRepository()).pack_order(3, "0")


class DeliveryAttemptRepositoryTests(TestCase):
    def test_second_attempt_uses_selected_delivery_date(self):
        connection = FakeConnection(one_rows=[(7, 1, "niet aanwezig")])

        AssessedRepository(connection).register_delivery_attempt(
            5, date(2026, 10, 31), True, time(14, 30), True
        )

        self.assertEqual(connection.commits, 1)
        query, parameters = connection.cursor_instance.statements[0]
        self.assertIn("r.ritdatum=%s", query)
        self.assertEqual(parameters, (5, date(2026, 10, 31)))
        self.assertEqual(connection.cursor_instance.statements[2][1], (5, 7, time(14, 30), "afgeleverd", True))
        self.assertIn("INSERT INTO Leveringregel", connection.cursor_instance.statements[3][0])

    def test_first_successful_attempt_records_delivered_order_lines(self):
        connection = FakeConnection(one_rows=[(None,)])

        AssessedRepository(connection).register_first_delivery_attempt(
            5, date(2026, 10, 31), True, True
        )

        self.assertEqual(connection.commits, 1)
        self.assertIn("lp.pogingnummer = 1", connection.cursor_instance.statements[0][0])
        self.assertEqual(
            connection.cursor_instance.statements[1][1],
            ("afgeleverd", True, 5),
        )
        self.assertIn(
            "INSERT INTO Leveringregel",
            connection.cursor_instance.statements[2][0],
        )

    def test_first_attempt_cannot_be_recorded_twice(self):
        connection = FakeConnection(one_rows=[("afgeleverd",)])

        with self.assertRaises(DomainError):
            AssessedRepository(connection).register_first_delivery_attempt(
                5, date(2026, 10, 31), True, True
            )

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(len(connection.cursor_instance.statements), 1)


class DistributionRouteTests(TestCase):
    def test_distribution_page_shows_order_and_collection_bin(self):
        app = create_app()
        app.testing = True
        schedule_row = {
            "levering_id": 8,
            "pogingnummer": 1,
            "geplande_tijd": time(9, 0),
            "resultaat": None,
            "bestelling_id": 3,
            "bedrijfsnaam": "Apotheek 3",
            "contactpersoon": "Contact",
            "telefoonnummer": "0612345678",
            "adres": "Voorbeeldstraat 1",
            "ritdatum": date(2026, 11, 1),
        }
        unscheduled_order = {
            "bestelling_id": 9,
            "gewenste_leverdatum": date(2026, 11, 1),
            "dagdeel": "ochtend",
            "spoed": False,
            "bedrijfsnaam": "Apotheek 9",
            "telefoonnummer": "0612345678",
            "afleveradres": "Voorbeeldstraat 9",
        }
        connection = FakeConnection(
            all_rows=[
                [distribution_row(3, 5, "VB-1", "A", True)],
                [{"productnaam": "Medicine A"}],
                [unscheduled_order],
                [{"koerier_id": 1, "naam": "Koerier A", "beschikbaar": True}],
                [schedule_row],
            ]
        )

        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=connection):
                response = client.get("/deliveries")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bestelling 3", response.data)
        self.assertIn(b"VB-1", response.data)
        self.assertIn(b"Verpakking registreren", response.data)
        self.assertIn(b"Registreer eerste poging", response.data)
        self.assertIn(b"Orders inplannen", response.data)
        self.assertIn(b"Koerier A", response.data)
        self.assertIn(b"Rit inplannen", response.data)

    def test_second_attempt_uses_selected_date_and_outcome(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection()

        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=connection):
                with patch("routes.distribution.AssessedRepository") as repository:
                    response = client.post(
                        "/deliveries/second-attempt",
                        data={
                            "day": "2026-10-31",
                            "delivery_id": "5",
                            "time": "14:30",
                            "outcome": "afgeleverd",
                            "receipt_signed": "1",
                        },
                    )

        self.assertEqual(response.status_code, 302)
        repository.return_value.register_delivery_attempt.assert_called_once_with(
            5, date(2026, 10, 31), True, time(14, 30), True
        )

    def test_first_attempt_route_records_delivery_outcome(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection()

        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=connection):
                with patch("routes.distribution.AssessedRepository") as repository:
                    response = client.post(
                        "/deliveries/first-attempt",
                        data={
                            "day": "2026-10-31",
                            "delivery_id": "5",
                            "outcome": "afgeleverd",
                            "receipt_signed": "1",
                        },
                    )

        self.assertEqual(response.status_code, 302)
        repository.return_value.register_first_delivery_attempt.assert_called_once_with(
            5, date(2026, 10, 31), True, True
        )

    def test_pack_route_redirects_after_recording_boxes(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection(
            one_rows=[
                {"bestelling_id": 3, "status_naam": "wordt verzameld"},
                {"unieke_code": "VB-1"},
            ],
            all_rows=[[{"deelorder_id": 5, "afgerond": True}]],
        )

        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=connection):
                response = client.post("/deliveries/3/pack", data={"box_count": "2"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/deliveries")
        self.assertEqual(connection.commits, 1)

    def test_release_route_redirects_after_releasing_order(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection(
            one_rows=[{"status_naam": "ingepakt", "aantal_verhuisdozen": 2}]
        )

        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=connection):
                response = client.post("/deliveries/3/release")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/deliveries")
        self.assertEqual(connection.commits, 1)
