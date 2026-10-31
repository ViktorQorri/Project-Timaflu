"""Regression checks for the two distinct first-visit delivery outcomes."""
import unittest
from datetime import date
from unittest.mock import patch
from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


class FirstDeliveryCursor:
    def __init__(self, state):
        self.state = state
        self.queries = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params=()):
        self.queries.append(query)
        if "SET resultaat='afgeleverd'" in query:
            self.state["result"] = "afgeleverd"
    def fetchone(self): return {"resultaat": self.state["result"]}


class DB:
    def __init__(self, result=None):
        self.state = {"result": result}
        self.c = FirstDeliveryCursor(self.state)
        self.commits = 0
        self.rollbacks = 0
    def cursor(self, dictionary=False): return self.c
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


class FirstDeliveryTests(unittest.TestCase):
    def test_signed_first_delivery(self):
        db = DB()
        repo = AssessedRepository(db)
        with self.assertRaises(DomainError):
            repo.record_first_attempt_delivery(1, date(2026, 10, 31), None)
        self.assertEqual(db.commits, 0)
        repo.record_first_attempt_delivery(1, date(2026, 10, 31), "yes")
        self.assertEqual(db.state["result"], "afgeleverd")
        self.assertEqual(db.commits, 1)
        self.assertTrue(any("UPDATE Bestelling" in q for q in db.c.queries))
        self.assertFalse(any("INSERT INTO Leverpoging" in q for q in db.c.queries))
        with self.assertRaises(DomainError):
            repo.record_first_attempt_delivery(1, date(2026, 10, 31), "yes")

    def test_route_and_template(self):
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="test")
        class Stub:
            def __init__(self): self.calls = []
            def record_first_attempt_delivery(self, *args): self.calls.append(args)
        stub = Stub()
        with patch("routes.distribution.get_connection", return_value=object()):
            with patch("routes.distribution.AssessedRepository", return_value=stub):
                with app.test_client() as client:
                    response = client.post("/deliveries/first-attempt/delivered", data={
                        "day": "2026-10-31", "delivery_id": "1", "signature_confirmed": "yes"})
                    self.assertEqual(response.status_code, 302)
        self.assertEqual(stub.calls, [(1, date(2026, 10, 31), "yes")])
        template = app.jinja_loader.get_source(app.jinja_env, "deliveries.html")[0]
        self.assertIn("distribution.first_attempt_delivered", template)
