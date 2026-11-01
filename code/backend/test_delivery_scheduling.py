"""Manual courier setup and scheduling for released orders."""

from datetime import date, datetime, time
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, DomainError
from repositories.distribution_repository import DistributionRepository
from services.distribution_service import DistributionService


class SchedulingCursor:
    def __init__(self, database):
        self.database = database
        self.statements = database.statements
        self.rowcount = 1
        self.lastrowid = None
        self.query = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.query = query
        self.statements.append((query, params))
        if "INSERT INTO Rit" in query:
            self.lastrowid = 10
        elif "INSERT INTO Levering" in query:
            self.lastrowid = 20

    def fetchone(self):
        if "SELECT status_naam, gewenste_leverdatum" in self.query:
            return self.database.order
        if "SELECT levering_id FROM Levering" in self.query:
            return self.database.existing_delivery
        if "SELECT koerier_id, beschikbaar" in self.query:
            return self.database.courier
        if "SELECT rit_id" in self.query:
            return self.database.existing_ride
        if "SELECT koerier_id FROM Koerier" in self.query:
            return self.database.courier_exists
        return None

    def fetchall(self):
        if "SELECT levering_id FROM Levering" in self.query:
            return [self.database.existing_delivery] if self.database.existing_delivery else []
        return []


class SchedulingDatabase:
    def __init__(
        self,
        order=None,
        existing_delivery=None,
        courier=None,
        existing_ride=None,
        courier_exists=None,
    ):
        self.order = order or {
            "status_naam": "verstuurd",
            "gewenste_leverdatum": date(2026, 11, 1),
        }
        self.existing_delivery = existing_delivery
        self.courier = courier or {"koerier_id": 3, "beschikbaar": True}
        self.existing_ride = existing_ride
        self.courier_exists = courier_exists or {"koerier_id": 3}
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return SchedulingCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class DeliverySchedulingTests(TestCase):
    def test_new_courier_starts_unavailable(self):
        database = SchedulingDatabase()

        DistributionRepository(database).create_courier("Koerier A")

        self.assertEqual(database.commits, 1)
        query, parameters = database.statements[0]
        self.assertIn("INSERT INTO Koerier", query)
        self.assertIn("FALSE", query)
        self.assertEqual(parameters, ("Koerier A",))

    def test_availability_change_locks_and_updates_courier(self):
        database = SchedulingDatabase()

        DistributionRepository(database).set_courier_availability(3, True)

        self.assertEqual(database.commits, 1)
        self.assertEqual(database.statements[0][1], (3,))
        self.assertEqual(database.statements[1][1], (True, 3))
        self.assertIn("UPDATE Koerier", database.statements[1][0])

    def test_schedule_creates_ride_delivery_and_first_attempt(self):
        database = SchedulingDatabase()

        delivery_date = DistributionRepository(database).schedule_delivery(
            12, 3, time(9, 15), "yes"
        )

        self.assertEqual(delivery_date, date(2026, 11, 1))
        self.assertEqual(database.commits, 1)
        self.assertEqual(database.rollbacks, 0)
        self.assertEqual(
            database.statements[-1][1],
            (20, 10, time(9, 15)),
        )
        self.assertTrue(any("INSERT INTO Rit" in query for query, _ in database.statements))
        self.assertTrue(
            any("INSERT INTO Levering" in query for query, _ in database.statements)
        )

    def test_regular_delivery_requires_region_confirmation(self):
        database = SchedulingDatabase()
        with self.assertRaisesRegex(ConflictError, "koeriersregio"):
            DistributionRepository(database).schedule_delivery(12, 3, time(9, 15))
        self.assertEqual(database.commits, 0)
        self.assertEqual(database.rollbacks, 1)

    def test_schedule_reuses_same_courier_route_for_that_date(self):
        database = SchedulingDatabase(existing_ride={"rit_id": 15})

        DistributionRepository(database).schedule_delivery(12, 3, time(10, 0), "yes")

        self.assertFalse(any("INSERT INTO Rit" in query for query, _ in database.statements))
        self.assertEqual(database.statements[-1][1], (20, 15, time(10, 0)))

    def test_urgent_delivery_rejects_delivery_after_three_hours(self):
        order = {
            "status_naam": "verstuurd", "gewenste_leverdatum": date(2026, 11, 1),
            "spoed": True, "besteld_op": datetime(2026, 11, 1, 10, 0),
        }
        late = SchedulingDatabase(order=order)
        with self.assertRaisesRegex(ConflictError, "binnen drie uur"):
            DistributionRepository(late).schedule_delivery(12, 3, time(13, 1))
        self.assertEqual(late.rollbacks, 1)
        self.assertEqual(late.commits, 0)

        on_time = SchedulingDatabase(order=order)
        DistributionRepository(on_time).schedule_delivery(12, 3, time(12, 30))
        self.assertEqual(on_time.commits, 1)

    def test_unavailable_courier_cannot_be_scheduled(self):
        database = SchedulingDatabase(courier={"koerier_id": 3, "beschikbaar": False})

        with self.assertRaises(ConflictError):
            DistributionRepository(database).schedule_delivery(12, 3, time(9, 15), "yes")

        self.assertEqual(database.commits, 0)
        self.assertEqual(database.rollbacks, 1)
        self.assertFalse(any("INSERT INTO Rit" in query for query, _ in database.statements))

    def test_already_scheduled_order_cannot_be_scheduled_twice(self):
        database = SchedulingDatabase(existing_delivery={"levering_id": 6})

        with self.assertRaises(ConflictError):
            DistributionRepository(database).schedule_delivery(12, 3, time(9, 15), "yes")

        self.assertEqual(database.rollbacks, 1)
        self.assertEqual(len(database.statements), 3)
        self.assertIn("JOIN Leverpoging", database.statements[-1][0])

    def test_service_rejects_invalid_ids_and_time(self):
        class NoWriteRepository:
            def schedule_delivery(self, *_):
                raise AssertionError("invalid input must not reach the repository")

        service = DistributionService(NoWriteRepository())
        with self.assertRaises(DomainError):
            service.schedule_delivery(0, 3, time(9, 15))
        with self.assertRaises(DomainError):
            service.schedule_delivery(12, 3, "09:15")

    def test_schedule_route_passes_manual_courier_and_time(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=object()):
                with patch("routes.distribution._service") as service:
                    service.return_value.schedule_delivery.return_value = date(2026, 11, 1)
                    response = client.post(
                        "/deliveries/schedule",
                        data={"order_id": "12", "courier_id": "3", "time": "09:15",
                              "region_confirmed": "yes"},
                    )

        self.assertEqual(response.status_code, 302)
        service.return_value.schedule_delivery.assert_called_once_with(
            12, 3, time(9, 15), "yes"
        )
        self.assertTrue(response.headers["Location"].endswith("day=2026-11-01"))

    def test_create_courier_route_saves_name(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.distribution._service") as service:
                response = client.post(
                    "/deliveries/couriers",
                    data={"name": "  Koerier A  "},
                )

        self.assertEqual(response.status_code, 302)
        service.return_value.create_courier.assert_called_once_with("  Koerier A  ")
