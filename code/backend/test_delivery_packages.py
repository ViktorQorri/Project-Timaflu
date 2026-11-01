"""Check sources required for school submissions; archive generation is a release action.

Product-description.md asks for backend, frontend and database deliverables. This
unit check establishes source presence, NOT that final ZIPs or live query output
have been produced (those require a separate release check).
"""
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[2]

class DeliverableSourceTests(TestCase):
    def test_school_delivery_source_files_are_present(self):
        required = (
            "code/backend/app.py",
            "code/backend/requirements.txt",
            "code/backend/domain/business.py",
            "code/frontend/templates/base.html",
            "code/frontend/templates/deliveries.html",
            "code/frontend/templates/order_picking.html",
            "code/frontend/static/css/style.css",
            "code/database/schema.sql",
            "code/database/queries.sql",
            "eer.mwb",
            "Documentation/Architecture/uml/src/use_cases/informatiesysteem.puml",
            "Documentation/Architecture/screens/README.md",
            "Documentation/brightspace/Product-description.md",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

    def test_all_screen_designs_have_an_activity_diagram(self):
        for number in range(1,29):
            with self.subTest(ad=number):
                screen = list((ROOT/"Documentation/Architecture/screens").glob(f"AD{number:02d}_*.html"))
                diagram = list((ROOT/"Documentation/Architecture/uml/src/activity_diagrams").glob(f"AD{number:02d}_*.puml"))
                self.assertTrue(screen, f"Missing screen for AD{number:02d}")
                self.assertTrue(diagram, f"Missing activity for AD{number:02d}")
