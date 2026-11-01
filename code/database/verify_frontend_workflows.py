"""Exercise real Timaflu frontend POST workflows against disposable MySQL data.

Only run after audit_ui_queries.py has loaded the isolated fictional fixture.
This script mutates that disposable database, not production data.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"code/backend"))

from app import create_app


def check() -> None:
    if (os.environ.get("TIMAFLU_TEST_ALLOW_RESET")!="isolated"
            or os.environ.get("TIMAFLU_TEST_MYSQL_HOST")!="127.0.0.1"):
        raise SystemExit("Refusing to mutate anything outside disposable local MySQL.")
    options=dict(
        host="127.0.0.1",
        port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        user=os.getenv("TIMAFLU_TEST_MYSQL_USER","root"),
        password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        database="timaflu_casus_test_94",
    )
    app=create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="only-temporary-test-environment",
        DB_HOST=options["host"],DB_PORT=options["port"],
        DB_USER=options["user"],DB_PASSWORD=options["password"],
        DB_NAME=options["database"],
        TIMAFLU_ADDRESS="TESTGEGEVENS: fictief afzenderadres",
    )
    # Each assertion must see the latest committed writes from Flask requests.
    connection=mysql.connector.connect(**options, autocommit=True)
    try:
        with app.test_client() as client:
            # Start with a real reserved order and dispatch it to robot A.
            response=client.post("/order-picking/orders/5/dispatch")
            assert response.status_code==302, ("dispatch",response.status_code,response.get_data(as_text=True)[:300])
            next_order=client.get("/api/robots/1/next?aisle=A")
            assert next_order.status_code==200,("robot_next",next_order.status_code)
            payload=next_order.get_json()
            assert payload["suborder"]["bestelling_id"]==5,payload
            suborder_id=payload["suborder"]["deelorder_id"]
            assert len(payload["lines"])==1 and payload["lines"][0]["product_id"]==1,payload
            scanned=client.post(
                "/api/picking-bins",
                json={"aisle":"A","sub_order_id":suborder_id,"bin_code":"TEST-BAK-A005"},
            )
            assert scanned.status_code==200,("scan",scanned.status_code,scanned.get_json())
            collected=client.post(
                "/api/robots/1/complete",
                json={"aisle":"A","suborder_id":suborder_id,
                      "collected":[{"product_id":1,"quantity":2}]},
            )
            assert collected.status_code==200,("collect",collected.status_code,collected.get_json())
            assert collected.get_json()["afgerond"] is True
            print("PASS orderpicking: reserved order -> robot -> scanned bin -> collected")

            # A packed order must be released, assigned to a courier and signed.
            for url,data in (
                ("/deliveries/5/pack",{"box_count":"1"}),
                ("/deliveries/5/release",{}),
                ("/deliveries/schedule",{"order_id":"5","courier_id":"1",
                                          "time":"10:30","region_confirmed":"yes"}),
            ):
                r=client.post(url,data=data)
                assert r.status_code==302,(url,r.status_code,r.get_data(as_text=True)[:400])
            with connection.cursor() as cur:
                cur.execute("SELECT levering_id FROM Levering WHERE bestelling_id=5")
                delivery=cur.fetchone()
            assert delivery, "No scheduled delivery for order 5"
            delivery_id=delivery[0]
            r=client.post(
                "/deliveries/first-attempt",
                data={"day":"2026-10-22","delivery_id":str(delivery_id),
                      "outcome":"afgeleverd","receipt_signed":"1"},
            )
            assert r.status_code==302,("first attempt",r.status_code,r.get_data(as_text=True)[:500])
            with connection.cursor(dictionary=True) as c:
                c.execute("SELECT status_naam FROM Bestelling WHERE bestelling_id=5")
                assert c.fetchone()["status_naam"]=="afgeleverd"
                c.execute("SELECT product_id,aantal_geleverd FROM Leveringregel WHERE levering_id=%s",(delivery_id,))
                lines=c.fetchall()
                assert len(lines)==1 and lines[0]["product_id"]==1 and lines[0]["aantal_geleverd"]==2,lines
            print("PASS distribution: pack -> release -> schedule -> signed delivery -> delivery lines")

            # A second scheduled attempt must also be a genuine executable form.
            r=client.post(
                "/deliveries/second-attempt",
                data={"day":"2026-10-22","delivery_id":"5",
                      "time":"15:30","outcome":"afgeleverd","receipt_signed":"1"},
            )
            assert r.status_code==302,("second attempt",r.status_code,r.get_data(as_text=True)[:500])
            with connection.cursor(dictionary=True) as c:
                c.execute("SELECT status_naam FROM Bestelling WHERE bestelling_id=9")
                assert c.fetchone()["status_naam"]=="afgeleverd"
                c.execute("SELECT product_id,aantal_geleverd FROM Leveringregel WHERE levering_id=5")
                lines=c.fetchall()
                assert len(lines)==1 and lines[0]["product_id"]==3 and lines[0]["aantal_geleverd"]==2,lines
            print("PASS distribution: second attempt -> signed delivery -> recorded lines")

            # Set a real minimum-stock shortage and confirm the lowest supplier.
            r=client.post("/stock/minimums/3",data={"minimumvoorraad":"20"})
            assert r.status_code==302,("minimum",r.status_code)
            r=client.get("/reorder?product_id=3")
            assert r.status_code==200,("reorder selection",r.status_code)
            assert "TEST Fabrikant" in r.get_data(as_text=True)
            r=client.post("/reorder",data={
                "product_id":"3","supplier_id":"1","quantity":"10","confirmed":"yes",
            })
            assert r.status_code==302,("confirm purchase",r.status_code,r.get_data(as_text=True)[:500])
            with connection.cursor(dictionary=True) as c:
                c.execute("SELECT status_naam,besteld_op FROM Inkoopbestelling ORDER BY inkoopbestelling_id DESC LIMIT 1")
                latest=c.fetchone()
                assert latest["status_naam"]=="besteld" and latest["besteld_op"] is not None,latest
            print("PASS purchasing: minimum stock -> cheapest supplier -> recorded order")

            r=client.post("/acquisition/prospects",data={
                "company_name":"TEST Evaluatie Apotheek",
                "contact_person":"TEST prospect contact",
                "contact_details":"0600000077",
                "address":"TEST Prospectstraat 7",
                "visit_date":"2026-09-16",
            })
            assert r.status_code==302,("acquisition",r.status_code,r.get_data(as_text=True)[:500])
            with connection.cursor() as c:
                c.execute("SELECT COUNT(*) FROM PotentieleKlant WHERE bedrijfsnaam='TEST Evaluatie Apotheek'")
                assert c.fetchone()[0]==1
            print("PASS acquisition: customer visit added to MySQL")
    finally:
        connection.close()


if __name__=="__main__":
    check()
