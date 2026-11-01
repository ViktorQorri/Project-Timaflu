"""Record real SQL and MySQL result rows for every frontend screen.

Read-only screen visits run against an isolated local MySQL DB; a separately
generated fictional invoice provides a non-empty invoice screen.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
from unittest.mock import patch
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

import mysql.connector
from app import create_app
from repositories.weekly_invoice_repository import WeeklyInvoiceRepository

ROOT = Path(__file__).resolve().parents[2]
DATABASE = "timaflu_casus_test_94"
OUT = ROOT / "deliverables/_query_get_evidence.md"
SCREENS = [
    ("/", "Home"),
    ("/customers?q=TEST", "Klanten zoeken: centrale klantgegevens"),
    ("/customers/1/edit", "Klantgegevens en adressen bewerken (AD07)"),
    ("/orders?q=Testmedicijn&quantity=1", "Telefonische verkoop en beschikbaarheid"),
    ("/orders/new", "Telefonische orderinvoer met actuele klant- en productgegevens"),
    ("/orders/status", "Bestellingen en echte orderstatus"),
    ("/orders?order=1", "Orderstatus zoeken op nummer (AD06)"),
    ("/orders/1/status", "Orderregels en geregistreerde tekortafspraken (AD06)"),
    ("/products", "Productcatalogus"),
    ("/products/new", "Product toevoegen: leverancierskeuze"),
    ("/products/1/edit", "Product bewerken"),
    ("/products/1/remove", "Product verwijderen"),
    ("/stock", "Minimumvoorraad"),
    ("/suppliers?product=Testmedicijn", "Goedkoopste leverancier"),
    ("/manufacturers", "Fabrikanten en contactgegevens"),
    ("/manufacturers/new", "Fabrikant toevoegen"),
    ("/manufacturers/1/edit", "Fabrikant bewerken"),
    ("/manufacturers/1/prices", "Inkoopprijzen van fabrikant beheren"),
    ("/reorder", "Inkoop bij minimumvoorraad"),
    ("/stock/minimums", "Minimumvoorraad per medicijn instellen"),
    ("/deliveries/1/label", "Adreslabel voor een werkelijk verpakte order"),
    ("/order-picking", "Orderpicking en geregistreerde bakken"),
    ("/deliveries?day=2026-10-22", "Distributierooster"),
    ("/invoices?customer_id=1", "Openstaande facturen"),
    ("/invoices/outstanding", "Openstaande klantfacturen en betalingsherinneringen"),
    ("/invoices/1/reminders/1", "Eerste betalingsherinnering, echte factuur en vast referentiemoment"),
    ("/invoices/weekly?week_start=2026-10-19", "Weekfacturen"),
    ("/invoices/issued/1", "Uitgegeven factuur"),
    ("/acquisition", "Acquisitie-opvolging"),
]
MODULES = ["routes.purchasing","routes.sales","routes.order_picking",
           "routes.distribution","routes.administration",
           "routes.weekly_invoices","routes.acquisition","routes.api"]


class RecorderCursor:
    def __init__(self, cursor, output):
        self.cursor = cursor
        self.output = output
        self.entry = None

    def execute(self, sql, params=()):
        self.cursor.execute(sql, params)
        self.entry = {"sql": "\n".join(line.rstrip() for line in sql.strip().splitlines()), "params": list(params or []),
                      "results": [], "row_count": 0}
        self.output.append(self.entry)

    def fetchall(self):
        rows = self.cursor.fetchall()
        self.entry["row_count"] = len(rows)
        self.entry["results"] = deepcopy(rows[:15])
        return rows

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is not None:
            self.entry["row_count"] += 1
            self.entry["results"].append(deepcopy(row))
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
        # A second fictitious pharmacy has a signed delivery that has NOT yet
        # been invoiced. This makes the weekly invoice overview nonempty while
        # keeping the already-issued historical invoice available for inspection.
        with cnx.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Adres (adres) VALUES (%s)",
                ("TEST: Factuuradres tweede apotheek, Breda",),
            )
            invoice_address = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Adres (adres) VALUES (%s)",
                ("TEST: Afleveradres tweede apotheek, Breda",),
            )
            delivery_address = cursor.lastrowid
            cursor.execute(
                """INSERT INTO Klant
                    (bedrijfsnaam, contactpersoon, telefoonnummer,
                     afleveradres_id, betaaladres_id)
                   VALUES (%s,%s,%s,%s,%s)""",
                ("TEST Tweede apotheek B.V.", "TEST tweede contact",
                 "0612345679", delivery_address, invoice_address),
            )
            customer2 = cursor.lastrowid
            cursor.execute(
                """INSERT INTO Klantkorting
                    (klant_id, kalenderjaar, percentage)
                   VALUES (%s,2026,5.00)""", (customer2,),
            )
            cursor.execute(
                """INSERT INTO Bestelling
                    (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                     gewenste_leverdatum, dagdeel, spoed, status_naam)
                   VALUES (%s,%s,%s,%s,%s,'ochtend',FALSE,'afgeleverd')""",
                (customer2, delivery_address, invoice_address,
                 "2026-10-20 09:00:00", "2026-10-22"),
            )
            order2 = cursor.lastrowid
            cursor.execute(
                """INSERT INTO Bestelregel
                    (bestelling_id, product_id, aantal, prijs_per_eenheid)
                   VALUES (%s,1,2,100.00)""", (order2,),
            )
            cursor.execute(
                "INSERT INTO Levering (bestelling_id) VALUES (%s)", (order2,),
            )
            delivery2 = cursor.lastrowid
            cursor.execute(
                """INSERT INTO Leveringregel
                    (levering_id, product_id, aantal_geleverd)
                   VALUES (%s,1,2)""", (delivery2,),
            )
            cursor.execute(
                """INSERT INTO Leverpoging
                    (levering_id, pogingnummer, rit_id, geplande_tijd,
                     resultaat, ontvangst_getekend)
                   VALUES (%s,1,1,'13:00:00','afgeleverd',TRUE)""",
                (delivery2,),
            )

            # Robot/orderpicking pages are database-backed: their repository
            # functions must be intercepted like every other employee screen.
            cursor.execute(
                """INSERT INTO Inkoopfactuur
                    (leverancier_id, factuurdatum, bedrag)
                   VALUES (1,'2026-10-20',155.00)"""
            )
            cursor.execute("INSERT INTO Robot (robot_id, gang) VALUES (1, 'A')")
            for status in ("wordt verzameld", "nieuw"):
                cursor.execute(
                    """INSERT INTO Bestelling
                        (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                         gewenste_leverdatum, dagdeel, spoed, status_naam)
                       VALUES (1,2,1,'2026-10-31 08:00:00',
                               '2026-11-03','ochtend',FALSE,%s)""",
                    (status,),
                )
                order_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Bestelregel
                        (bestelling_id, product_id, aantal, prijs_per_eenheid)
                       VALUES (%s,1,1,100.00)""", (order_id,),
                )
                cursor.execute(
                    """INSERT INTO Voorraadreservering
                        (bestelling_id, product_id, aantal)
                       VALUES (%s,1,1)""", (order_id,),
                )
                if status == "wordt verzameld":
                    cursor.execute(
                        """INSERT INTO Deelorder
                            (bestelling_id, robot_id, afgerond)
                           VALUES (%s,1,FALSE)""", (order_id,),
                    )
                    suborder_id = cursor.lastrowid
                    cursor.execute(
                        """INSERT INTO Deelorderregel
                            (deelorder_id, product_id, aantal)
                           VALUES (%s,1,1)""", (suborder_id,),
                    )
                    cursor.execute(
                        """INSERT INTO Verzamelbak (unieke_code, deelorder_id)
                           VALUES ('TEST-BAK-A',%s)""", (suborder_id,),
                    )
        # Fictional historical delivery is packed, so its real label can be
        # inspected without inventing a successful live robot operation.
        with cnx.cursor() as cursor:
            cursor.execute(
                "UPDATE Bestelling SET aantal_verhuisdozen=1 WHERE bestelling_id=1"
            )
        cnx.commit()
    finally:
        cnx.close()

    app = create_app()
    # Prove that every employee-facing GET route is represented in this
    # executable query-output deliverable. The robot API is not a screen.
    adapter = app.url_map.bind("localhost")
    audited_endpoints = {
        adapter.match(urlsplit(url).path, method="GET")[0]
        for url, _ in SCREENS
    }
    untested = sorted(
        rule.endpoint for rule in app.url_map.iter_rules()
        if "GET" in rule.methods and rule.endpoint not in {
            "static", "api.next_robot_order"
        } and rule.endpoint not in audited_endpoints
    )
    if untested:
        raise SystemExit("Employee-facing GET screens lacking MySQL evidence: "
                         + ", ".join(untested))
    app.config.update(TESTING=True,SECRET_KEY="testkey",
                      DB_HOST=options["host"],DB_PORT=options["port"],
                      DB_NAME=DATABASE,DB_USER=options["user"],
                      DB_PASSWORD=options["password"],TIMAFLU_ADDRESS=sender)
    version_connection = mysql.connector.connect(**options)
    try:
        with version_connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            mysql_version = cursor.fetchone()[0]
    finally:
        version_connection.close()
    report = [
        "# Werkelijke MySQL-query-output per scherm",
        "",
        f"Uitgevoerd op geïsoleerde MySQL {mysql_version} met fictieve fixturegegevens.",
        "Elke query hieronder is tijdens het echte GET-verzoek van de Flask-app",
        "onderschept en de getoonde rijen zijn afkomstig van MySQL, niet verzonnen.",
        "Schermen zonder dynamische databasegegevens zijn expliciet als statisch vermeld.",
        "De robotinterface /api/robots/<id>/next is geen medewerkersscherm:",
        "deze API wordt afzonderlijk op gang-/robotvalidatie getest.",
        "",
    ]
    count = 0
    failures = []
    audited_urls = set()
    with app.test_client() as client:
        for url, heading in SCREENS:
            audited_urls.add(url)
            statements=[]
            conn = mysql.connector.connect(**options)
            proxy = RecorderConnection(conn, statements)
            try:
                with ExitStack() as stack:
                    for module in MODULES:
                        stack.enter_context(patch(
                            module+".get_connection", return_value=proxy
                        ))
                    if url == "/invoices/1/reminders/1":
                        # The fictional invoice is dated 2026-10-31. Simulate
                        # 2026-11-08 (8 days later) to exercise an actually due
                        # postal reminder without changing any invoice or
                        # reminder row in the isolated test database.
                        audit_date = stack.enter_context(
                            patch("routes.administration.date")
                        )
                        audit_date.today.return_value = date(2026, 11, 8)
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(report),encoding="utf-8")
    print(f"Screen audit: {len(SCREENS)} screens, {count} actual queries, failures: {failures}")
    if failures:
        raise SystemExit("Non-200 screen responses: "+", ".join(failures))


if __name__ == "__main__":
    main()
