"""Opt-in real MySQL locking test for robot suborders (isolated database only).

Run only with TIMAFLU_TEST_MYSQL=isolated after loading schema.sql in a disposable
database. Never connect this test to production.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import TestCase, skipUnless

import mysql.connector

from repositories.robot_order_repository import RobotOrderRepository


@skipUnless(os.environ.get("TIMAFLU_TEST_MYSQL") == "isolated",
            "Requires disposable MySQL schema and explicit opt-in")
class RobotMySQLConcurrencyTests(TestCase):
    @staticmethod
    def connection():
        return mysql.connector.connect(
            host=os.environ["TIMAFLU_TEST_HOST"],
            port=int(os.environ["TIMAFLU_TEST_PORT"]),
            user=os.environ["TIMAFLU_TEST_USER"],
            password=os.environ["TIMAFLU_TEST_PASSWORD"],
            database=os.environ["TIMAFLU_TEST_DATABASE"],
        )

    def test_parallel_generation_and_completion_are_serialized(self):
        db = self.connection()
        try:
            with db.cursor() as cur:
                cur.execute("INSERT INTO Adres (adres) VALUES ('Teststraat 1')")
                address = cur.lastrowid
                cur.execute(
                    """INSERT INTO Klant (bedrijfsnaam, afleveradres_id, betaaladres_id)
                       VALUES ('Testapotheek', %s, %s)""", (address, address))
                customer = cur.lastrowid
                cur.execute(
                    """INSERT INTO Product (artikelnummer, bestelcode, productnaam,
                       prijs_per_grootverpakking, aantal_detailverpakkingen,
                       minimale_bestelhoeveelheid, minimumvoorraad)
                       VALUES ('TIMA-CONC-1', 'TIMA-CONC-CODE', 'Testmedicijn',
                               10.00, 1, 1, 1)""")
                product = cur.lastrowid
                cur.execute(
                    "INSERT INTO Robot (robot_id, gang) VALUES (1, 'A')")
                cur.execute(
                    """INSERT INTO Magazijnlocatie (gang, schapnummer, product_id, aantal)
                       VALUES ('A', 1, %s, 5)""", (product,))
                cur.execute(
                    """INSERT INTO Bestelling (klant_id, afleveradres_id, betaaladres_id,
                       besteld_op, gewenste_leverdatum, dagdeel, spoed, status_naam)
                       VALUES (%s, %s, %s, NOW(), DATE_ADD(CURDATE(), INTERVAL 1 DAY),
                               'ochtend', FALSE, 'wordt verzameld')""",
                    (customer, address, address))
                order = cur.lastrowid
                cur.execute(
                    """INSERT INTO Bestelregel
                       (bestelling_id, product_id, aantal, prijs_per_eenheid)
                       VALUES (%s, %s, 3, 10.00)""",
                    (order, product))
                cur.execute(
                    """INSERT INTO Voorraadreservering
                       (bestelling_id, product_id, aantal) VALUES (%s, %s, 3)""",
                    (order, product))
            db.commit()
        finally:
            db.close()

        barrier = Barrier(2)

        def attempt_generation():
            conn = self.connection()
            try:
                barrier.wait(timeout=10)
                try:
                    return ("success", RobotOrderRepository(conn).generate(order))
                except Exception as error:
                    return (type(error).__name__, str(error))
            finally:
                conn.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt_generation(), range(2)))
        self.assertEqual([x[0] for x in results].count("success"), 1)
        self.assertEqual([x[0] for x in results].count("ConflictError"), 1)
        suborder = next(x[1][0]["suborder_id"] for x in results if x[0] == "success")
        conn = self.connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM Deelorder WHERE bestelling_id=%s", (order,))
                self.assertEqual(cur.fetchone()[0], 1)
                cur.execute("INSERT INTO Verzamelbak (unieke_code, deelorder_id) VALUES ('TIMA-CONC-BIN', %s)", (suborder,))
            conn.commit()
        finally:
            conn.close()

        barrier2 = Barrier(2)

        def attempt_completion():
            conn = self.connection()
            try:
                barrier2.wait(timeout=10)
                try:
                    return ("success", RobotOrderRepository(conn).complete(1, suborder))
                except Exception as error:
                    return (type(error).__name__, str(error))
            finally:
                conn.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            completed = list(pool.map(lambda _: attempt_completion(), range(2)))
        self.assertEqual([x[0] for x in completed].count("success"), 1)
        self.assertEqual([x[0] for x in completed].count("ConflictError"), 1)
        conn = self.connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT afgerond FROM Deelorder WHERE deelorder_id=%s", (suborder,))
                self.assertEqual(cur.fetchone()[0], 1)
        finally:
            conn.close()
