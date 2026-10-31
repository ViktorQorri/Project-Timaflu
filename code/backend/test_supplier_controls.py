"""Two manual purchasing decisions from the Timaflu case require confirmation."""
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app


class SupplierStub:
    calls=[]
    def __init__(self, connection): pass
    def find_offers(self, product_name):
        return [{
            "product_id":1, "productnaam":"Testmedicijn",
            "leverancier_id":2,"leverancier":"Testfabrikant",
            "contactpersoon":"Testcontact","telefoonnummer":"0612345678",
            "inkoopprijs":Decimal("12.00"),
        }]
    def remove_offer(self, product_id, supplier_id):
        self.calls.append(("offer",product_id,supplier_id))
        return 1
    def remove_from_internal_reorder_list(self, product_id):
        self.calls.append(("internal",product_id))
        return 1


class SupplierControlTests(TestCase):
    def setUp(self):
        SupplierStub.calls=[]
        self.app=create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test")
    def test_supplier_screen_has_both_case_actions(self):
        with patch("routes.purchasing.get_connection",return_value=object()):
            with patch("routes.purchasing.SupplierRepository",SupplierStub):
                response=self.app.test_client().get("/suppliers?product=Testmedicijn")
        self.assertEqual(response.status_code,200)
        self.assertIn(b"Leverancier loskoppelen",response.data)
        self.assertIn(b"Verwijder uit interne bestellijst",response.data)
        self.assertIn(b"Testfabrikant",response.data)

    def test_supplier_changes_require_manual_confirmation(self):
        with patch("routes.purchasing.get_connection",return_value=object()):
            with patch("routes.purchasing.SupplierRepository",SupplierStub):
                with self.app.test_client() as client:
                    no=client.post("/suppliers/remove-offer",
                        data={"product_id":"1","supplier_id":"2"})
                    self.assertEqual(no.status_code,400)
                    self.assertEqual(SupplierStub.calls,[])
                    yes=client.post("/suppliers/remove-offer",data={
                        "product_id":"1","supplier_id":"2",
                        "product_name":"Testmedicijn","confirmed":"yes"})
                    self.assertEqual(yes.status_code,302)
                    no=client.post("/suppliers/remove-product",data={"product_id":"1"})
                    self.assertEqual(no.status_code,400)
                    yes=client.post("/suppliers/remove-product",data={
                        "product_id":"1","confirmed":"yes","product_name":"Testmedicijn"})
                    self.assertEqual(yes.status_code,302)
        self.assertEqual(
            SupplierStub.calls,[("offer",1,2),("internal",1)]
        )
