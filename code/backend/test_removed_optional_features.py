from unittest import TestCase
from app import create_app
class RemovedFeaturesTests(TestCase):
    def test_routes_removed(self):
        a=create_app()
        a.testing=True
        with a.test_client() as c:
            for method,path in (("get","/reports"),("get","/api/health"),("get","/customers/1/deactivate"),("post","/customers/1/deactivate")):
                self.assertEqual(getattr(c,method)(path).status_code,404)
