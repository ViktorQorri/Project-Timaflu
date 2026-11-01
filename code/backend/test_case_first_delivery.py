"""Regressies voor een ondertekende eerste aflevering zonder extra bezoek."""
import unittest
from datetime import date, time
from unittest.mock import patch
from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository
from test_distribution import FakeConnection


class FirstDeliveryTests(unittest.TestCase):
    def test_signed_first_delivery(self):
        with self.assertRaises(DomainError):
            AssessedRepository(None).register_first_delivery_attempt(
                1, date(2026, 10, 31), True, False
            )
        db=FakeConnection(one_rows=[{
            "resultaat":None,"geplande_tijd":time(9),"rit_id":5,
        }])
        AssessedRepository(db).register_first_delivery_attempt(
            1,date(2026,10,31),True,True
        )
        self.assertEqual(db.commits,1)
        statements=[q for q,_ in db.cursor_instance.statements]
        self.assertTrue(any("INSERT INTO Leveringregel" in q for q in statements))
        self.assertFalse(any("INSERT INTO Leverpoging" in q for q in statements))
        with self.assertRaises(DomainError):
            duplicate=FakeConnection(one_rows=[{
                "resultaat":"afgeleverd","geplande_tijd":time(9),"rit_id":5,
            }])
            AssessedRepository(duplicate).register_first_delivery_attempt(
                1,date(2026,10,31),True,True
            )

    def test_route_and_template(self):
        app=create_app()
        app.config.update(TESTING=True,SECRET_KEY="test")
        class Stub:
            def __init__(self):self.calls=[]
            def register_first_delivery_attempt(self,*args):self.calls.append(args)
        stub=Stub()
        with patch("routes.distribution.get_connection",return_value=object()):
            with patch("routes.distribution.AssessedRepository",return_value=stub):
                with app.test_client() as client:
                    response=client.post("/deliveries/first-attempt",data={
                        "day":"2026-10-31","delivery_id":"1",
                        "outcome":"afgeleverd","receipt_signed":"1"
                    })
        self.assertEqual(response.status_code,302)
        self.assertEqual(stub.calls,[(1,date(2026,10,31),True,True,None)])
        template=app.jinja_loader.get_source(app.jinja_env,"deliveries.html")[0]
        self.assertIn("distribution.first_attempt",template)
