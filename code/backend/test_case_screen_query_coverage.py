"""Every employee-facing GET screen must have measured MySQL query output."""
import ast
from pathlib import Path
from unittest import TestCase
from urllib.parse import urlsplit

from app import create_app

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = ROOT / "code/database/audit_ui_queries.py"


class ScreenQueryCoverageTests(TestCase):
    def test_all_flask_stylesheet_references_exist(self):
        # Broken shared CSS links cause 404 on every rendered page.
        import re
        templates = ROOT / "code/frontend/templates"
        static = ROOT / "code/frontend/static"
        missing = []
        for template in templates.glob("*.html"):
            source = template.read_text(encoding="utf-8")
            for relative in re.findall(
                r"url_for\('static',\s*filename='([^']+)'\)", source
            ):
                if not (static / relative).is_file():
                    missing.append(f"{template.name}: {relative}")
        self.assertEqual(missing, [], "Missing referenced local static assets")

    def test_no_employee_get_route_lacks_query_evidence(self):
        source = ast.parse(AUDITOR.read_text(encoding="utf-8"))
        screen_urls = None
        for statement in source.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "SCREENS"
                for target in statement.targets
            ):
                screen_urls = [url for url, _ in ast.literal_eval(statement.value)]
                break
        self.assertIsNotNone(screen_urls)
        app = create_app()
        adapter = app.url_map.bind("localhost")
        covered = {
            adapter.match(urlsplit(url).path, method="GET")[0]
            for url in screen_urls
        }
        # Robot JSON dispatch has no human-facing screen; /api/health is
        # included to demonstrate the actual database connection.
        excluded = {"static", "api.next_robot_order"}
        missing = sorted(
            rule.endpoint
            for rule in app.url_map.iter_rules()
            if "GET" in rule.methods
            and rule.endpoint not in excluded
            and rule.endpoint not in covered
        )
        self.assertEqual(missing, [], "Missing MySQL evidence for employee screens")
