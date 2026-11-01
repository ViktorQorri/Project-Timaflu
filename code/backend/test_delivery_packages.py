"""School deliverable ZIPs must be complete, readable and free of local secrets."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from zipfile import ZipFile

CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))
from build_deliverables import build  # noqa: E402


class DeliverableArchivesTests(TestCase):
    def test_all_four_archives_contain_school_required_sources(self):
        expected = {
            "timaflu-backend.zip": [
                "code/backend/app.py", "code/backend/requirements.txt",
                "code/backend/domain/business.py", "code/README.md",
            ],
            "timaflu-frontend.zip": [
                "code/frontend/templates/base.html", "code/frontend/templates/deliveries.html",
                "code/frontend/templates/order_picking.html",
                "code/frontend/static/css/style.css",
            ],
            "timaflu-database-en-queries.zip": [
                "code/database/schema.sql", "code/database/queries.sql",
                "Documentation/Architecture/eer-mysql-verified.drawio",
                "Documentation/Architecture/query-output-per-screen.md",
            ],
            "timaflu-ontwerpen.zip": [
                "Documentation/Architecture/class-diagram-backend.puml",
                "Documentation/Architecture/screens/README.md",
                "Documentation/brightspace/Product-description.md",
            ],
        }
        with TemporaryDirectory(prefix="timaflu-deliverables-") as temp:
            files = build(Path(temp))
            self.assertEqual(set(files), set(expected))
            for archive, required in expected.items():
                with self.subTest(archive=archive), ZipFile(Path(temp) / archive) as zipped:
                    names = zipped.namelist()
                    self.assertIsNone(zipped.testzip())
                    self.assertEqual(len(names), len(set(names)))
                    for item in required:
                        self.assertIn(item, names)
                    self.assertFalse(any(
                        part in {"__pycache__", ".git", "node_modules"}
                        or item.endswith((".pyc", ".pyo"))
                        or part == ".env"
                        for item in names for part in Path(item).parts
                    ))
