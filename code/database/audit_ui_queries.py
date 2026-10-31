"""Record real SQL and MySQL result rows for every frontend screen.

Read-only screen visits run against an isolated local MySQL DB; a separately
generated fictional invoice provides a non-empty invoice screen.
"""
from contextlib import ExitStack
from datetime import date
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

import mysql.connector
from app import create_app
from repositories.weekly_invoice_repository import WeeklyInvoiceRepository

ROOT = Path(__file__).resolve().parents[2]
DATABASE = "timaflu_casus_test_94"
OUT = ROOT / "Documentation/Architecture/query-output-per-screen.md"
SCREENS = [
    ("/", "Home en databasecontrole"),
    ("/customers", "Klanten (statisch scherm)"),
    ("/orders?q=Testmedicijn&quantity=1", "Telefonische verkoop en beschikbaarheid"),
    ("/products", "Productcatalogus"),
    ("/products/new", "Product toevoegen: leverancierskeuze"),
    ("/products/1/edit", "Product bewerken"),
    ("/products/1/remove", "Product verwijderen"),
    ("/stock", "Minimumvoorraad"),
    ("/suppliers?product=Testmedicijn", "Goedkoopste leverancier"),
    ("/order-picking", "Orderpicking (statisch scherm)"),
    ("/deliveries?day=2026-10-22", "Distributierooster"),
    ("/invoices?customer_id=1", "Openstaande facturen"),
    ("/invoices/weekly?week_start=2026-10-19", "Weekfacturen"),
    ("/invoices/issued/1", "Uitgegeven factuur"),
    ("/acquisition", "Acquisitie-opvolging"),
    ("/reports", "Rapportage (statisch scherm)"),
    ("/api/health", "Database API gezondheid"),
]
MODULES = ["routes.home","routes.purchasing","routes.sales",
           "routes.distribution","routes.administration",
           "routes.weekly_invoices","routes.acquisition","routes.api"]


class RecorderCursor:
    def __init__(self, cursor, output):
        self.cursor = cursor
        self.output = output
        self.entry = None

    def execute(self, sql, params=()):
        self.cursor.execute(sql, params)
        self.entry = {"sql": " ".join(sql.split()), "params": list(params or []),
                      "results": [], "row_count": 0}
        self.output.append(self.entry)

    def fetchall(self):
        rows = self.cursor.fetchall()
        self.entry["row_count"] = len(rows)
        self.entry["results"] = rows[:15]
        return rows

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is not None:
            self.entry["row_count"] += 1
            self.entry["results"].append(row)
        return row

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()
        return False

    def __getattr__(self, key):
        return getattr(self.cursor, key)


class RecorderConnection:
    def __init__(self, connection, output):
        self.connection = connection
        self.output = output

    def cursor(self, **kwargs):
        return RecorderCursor(self.connection.cursor(**kwargs), self.output)

    def __getattr__(self, key):
        return getattr(self.connection, key)


def main():
    if (os.getenv("TIMAFLU_TEST_ALLOW_RESET") != "isolated"
            or os.getenv("TIMAFLU_TEST_MYSQL_HOST") != "127.0.0.1"):
        raise SystemExit("Only isolated localhost MySQL may be audited")
    options = dict(
        host="127.0.0.1", port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        user=os.getenv("TIMAFLU_TEST_MYSQL_USER","root"),
        password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"], database=DATABASE
    )
    sender="TESTGEGEVENS: Fictieve Afzenderstraat 9, Breda"
    # Reset ONLY the explicitly isolated fixture DB to make the query-output
    # deterministic and independent from the test execution order.
    admin_opts={key:value for key,value in options.items() if key!="database"}
    admin=mysql.connector.connect(**admin_opts)
    try:
        with admin.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {DATABASE}")
            cursor.execute(f"CREATE DATABASE {DATABASE} CHARACTER SET utf8mb4")
        admin.commit()
    finally:
        admin.close()
    cnx = mysql.connector.connect(**options)
    try:
        for path in (
            ROOT/"code/database/schema.sql",
            ROOT/"Documentation/Architecture/test-data/weekly_invoicing_fixture.sql"
        ):
            content="\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                               if not line.lstrip().startswith("--"))
            with cnx.cursor() as cursor:
                for statement in content.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
        cnx.commit()
        WeeklyInvoiceRepository(cnx).issue_week(
            date(2026,10,19),sender,date(2026,10,31)
        )
    finally:
        cnx.close()

    app = create_app()
    app.config.update(TESTING=True,SECRET_KEY="testkey",
                      DB_HOST=options["host"],DB_PORT=options["port"],
                      DB_NAME=DATABASE,DB_USER=options["user"],
                      DB_PASSWORD=options["password"],TIMAFLU_ADDRESS=sender)
    report = [
        "# Werkelijke MySQL-query-output per scherm",
        "",
        "Uitgevoerd op geïsoleerde MySQL 8.4.13 met fictieve fixturegegevens.",
        "Elke query hieronder is tijdens het echte GET-verzoek van de Flask-app",
        "onderschept en de getoonde rijen zijn afkomstig van MySQL, niet verzonnen.",
        "Schermen zonder dynamische databasegegevens zijn expliciet als statisch vermeld.",
        "",
    ]
    count = 0
    failures = []
    with app.test_client() as client:
        for url, heading in SCREENS:
            statements=[]
            conn = mysql.connector.connect(**options)
            proxy = RecorderConnection(conn, statements)
            try:
                with ExitStack() as stack:
                    for module in MODULES:
                        stack.enter_context(patch(
                            module+".get_connection", return_value=proxy
                        ))
                    response = client.get(url)
                report += [f"## {heading}", "", f"Scherm: {url}",
                           f"HTTP-status: {response.status_code}", ""]
                if response.status_code != 200:
                    failures.append(f"{url} => {response.status_code}")
                if not statements:
                    report += ["*Geen SQL-query: statisch/placeholder-scherm.*", ""]
                for index, entry in enumerate(statements,1):
                    count += 1
                    report += [
                        f"### Query {index}",
                        "```sql", entry["sql"], "```",
                        "Parameters: ```json",
                        json.dumps(entry["params"],ensure_ascii=False,default=str),
                        "```",
                        f"Resultaat: {entry['row_count']} rij(en) (maximaal 15 getoond)",
                        "```json",
                        json.dumps(entry["results"],indent=2,ensure_ascii=False,default=str),
                        "```", "",
                    ]
            finally:
                conn.close()
    OUT.write_text("\n".join(report),encoding="utf-8")
    print(f"Screen audit: {len(SCREENS)} screens, {count} actual queries, failures: {failures}")
    if failures:
        raise SystemExit("Non-200 screen responses: "+", ".join(failures))


if __name__ == "__main__":
    main()
