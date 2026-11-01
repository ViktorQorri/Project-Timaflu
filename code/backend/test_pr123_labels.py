"""Address labels and shelf locations from the required order-picking process."""
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, NotFoundError
from repositories.distribution_repository import DistributionRepository
from repositories.robot_order_repository import RobotOrderRepository


class Cursor:
    def __init__(self, row):
        self.row = row
        self.query = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.row

    def fetchall(self):
        return [self.row] if self.row else []


class DB:
    def __init__(self, row):
        self.cur = Cursor(row)

    def cursor(self, dictionary=False):
        return self.cur


class LabelAndRobotLocationTests(TestCase):
    def test_robots_receive_shelf_locations_in_own_aisle(self):
        db = DB({"product_id": 8, "aantal": 2, "magazijnlocaties": "A4, A8"})
        result = RobotOrderRepository(db).suborder_lines(12)
        self.assertEqual(result[0]["magazijnlocaties"], "A4, A8")
        self.assertIn("m.gang = r.gang", db.cur.query)
        self.assertIn("GROUP_CONCAT", db.cur.query)
        self.assertEqual(db.cur.params, (12,))

    def test_label_requires_existing_packed_order(self):
        with self.assertRaises(NotFoundError):
            DistributionRepository(DB(None)).packing_label(20)
        with self.assertRaises(ConflictError):
            DistributionRepository(DB({"aantal_verhuisdozen": 0})).packing_label(20)

    def test_label_displays_address_phone_and_rush_marker(self):
        app = create_app()
        app.testing = True
        label = {
            "bestelling_id": 20, "aantal_verhuisdozen": 2,
            "bedrijfsnaam": "Apotheek Centrum",
            "afleveradres": "Teststraat 10", "telefoonnummer": "0612345678",
            "spoed": True,
        }
        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=object()):
                with patch("routes.distribution.DistributionRepository") as repository:
                    repository.return_value.packing_label.return_value = label
                    response = client.get("/deliveries/20/label")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Apotheek Centrum", response.data)
        self.assertIn(b"Teststraat 10", response.data)
        self.assertIn(b"0612345678", response.data)
        self.assertIn(b"SPOED", response.data)
        self.assertIn(b"@media print", response.data)
