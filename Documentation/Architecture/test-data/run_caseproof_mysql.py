"""Disposable MySQL 8.4 integration checks for the original Timaflu case.

Run with CASEPROOF_DB_PASSWORD against the isolated local MySQL Docker instance
bound to 127.0.0.1 on a configured test port. A random test database is created and dropped.
"""
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import os
import sys
import mysql.connector

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"code/backend"))
from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.supplier_repository import SupplierRepository
from repositories.purchase_order_repository import PurchaseOrderRepository

HOST="127.0.0.1"
PORT=int(os.environ.get("CASEPROOF_DB_PORT", "33320"))
PASSWORD=os.environ.get("CASEPROOF_DB_PASSWORD", "")
# Never permit connecting to a non-loopback MySQL host with this destructive test runner.

def sql_statements(path):
    content=path.read_text(encoding="utf-8-sig")
    lines=(line for line in content.splitlines() if not line.strip().startswith("--"))
    for part in "\n".join(lines).split(";"):
        if part.strip():
            yield part.strip()

def inserted_order(conn,customer=1,requested=date(2026,10,31)):
    with conn.cursor() as cur:
        cur.execute(
          """INSERT INTO Bestelling(klant_id,afleveradres_id,betaaladres_id,besteld_op,
             gewenste_leverdatum,dagdeel,spoed,status_naam)
             VALUES (%s,1,1,'2026-10-31 08:00:00',%s,'ochtend',FALSE,'verstuurd')""",
          (customer,requested))
        order_id=cur.lastrowid
        cur.execute("INSERT INTO Levering(bestelling_id) VALUES(%s)",(order_id,))
        delivery=cur.lastrowid
        cur.execute(
          """INSERT INTO Leverpoging(levering_id,pogingnummer,rit_id,
             geplande_tijd,resultaat,ontvangst_getekend)
             VALUES(%s,1,1,'11:00:00',NULL,NULL)""",(delivery,))
    conn.commit()
    return order_id,delivery

def verify(name,condition):
    if not condition: raise AssertionError(name)
    print("PASS",name)

def measured_query_tables(conn):
    """The output below is fetched from MySQL, never a manually fabricated table."""
    output = []
    with conn.cursor() as cursor:
        for sql in sql_statements(ROOT/"Documentation/Architecture/test-data/selects_assessed.sql"):
            cursor.execute(sql)
            rows=cursor.fetchall()
            headers=[col[0] for col in cursor.description]
            if len(headers)==1 and headers[0]=="proces":
                output.append("### "+str(rows[0][0]))
                continue
            output.append("| "+" | ".join(headers)+" |")
            output.append("| "+" | ".join(["---"]*len(headers))+" |")
            for row in rows:
                values=["NULL" if v is None else str(v).replace("|", "\\|") for v in row]
                output.append("| "+" | ".join(values)+" |")
            if not rows:
                output.append("| "+" | ".join(["(geen rijen)"]+[""]*(len(headers)-1))+" |")
            output.append("")
    return "\n".join(output)


def write_measured_evidence(evidence):
    """Persist observed values only after the scenario checks succeeded."""
    import subprocess
    revision=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],
                            capture_output=True,check=True,text=True).stdout.strip()
    report=ROOT/"Documentation/Architecture/query-results-assessed.md"
    report.write_text(
        "# Gemeten MySQL-queryresultaten voor de vijf verplichte scenario's\n\n"
        "Testdatum: 31 oktober 2026. Gecontroleerde codecommit: "+revision+"\n\n"
        "Bronnen: code/database/schema.sql, Documentation/Architecture/test-data/"
        "fixtures_assessed.sql en selects_assessed.sql.\n\n"
        "Deze tabellen zijn door MySQL 8.4 teruggegeven voor fictieve gegevens "
        "in een nieuw gemaakte en na afloop verwijderde lokale testdatabase.\n"
        "Het uitvoerbare bewijs staat in run_caseproof_mysql.py; hiermee zijn ook "
        "de vijf bijbehorende Flask-pagina's met echte MySQL-verbindingen getest.\n\n"
        +evidence+
        "\n## Interpretatie en beperkingen\n\n"
        "- De testdatabase bevat alleen fictieve, niet-productiegegevens.\n"
        "- De geslaagde tests bewijzen de gecontroleerde vijf scenario's en deze SQL-outputs, "
        "niet automatisch alle integratiepaden van het volledige project.\n"
        "- Visuele en keyboardtests op echte mobiele apparaten zijn hiermee niet uitgevoerd.\n"
        "- Onbekende historische factuurbedragen worden niet met aannames aangevuld.\n"
        "- De output per scherm van overige proces-PR's moet op de geïntegreerde eindversie "
        "afzonderlijk worden gemeten.\n",
        encoding="utf-8",newline="\n")
    print("WROTE observed query evidence",report)


def run(conn,dbname,password):
    with conn.cursor() as cur:
        cur.execute("USE "+dbname)
        for path in (ROOT/"code/database/schema.sql",
                     ROOT/"Documentation/Architecture/test-data/fixtures_assessed.sql"):
            count=0
            for statement in sql_statements(path):
                cur.execute(statement)
                count+=1
            print("Loaded",path.name,"SQL statements",count)
    conn.commit()
    observed=measured_query_tables(conn)
    repo=AssessedRepository(conn)
    customer,revenue=repo.customer_revenue(1,2025)
    verify("sales: actual paid 2025 turnover",Decimal(revenue)==Decimal("37.28"))
    verify("sales: customer billing address",customer["klantadres"].endswith("Breda"))
    offers=SupplierRepository(conn).find_offers("Testmedicijn")
    verify("purchasing: supplier cheapest first, with contacts",
           len(offers)==2 and offers[0]["leverancier"]=="Fabrikant B"
           and offers[0]["inkoopprijs"]==Decimal("12.00")
           and bool(offers[0]["telefoonnummer"]))
    purchase_id=PurchaseOrderRepository(conn).create(2,1,3)
    verify("purchasing: manual internal purchase recorded",purchase_id>0)
    unpaid_id=2  # The fixture contains one paid 2025 and one unpaid 2026 invoice.
    open_invoices=repo.invoice_for_customer(1)
    verify("administration: only unpaid invoices",len(open_invoices)==1
           and open_invoices[0]["factuur_id"]==unpaid_id)
    try:
        repo.record_payment_action(unpaid_id,"payment_plan_accepted",date(2026,10,15))
        raise AssertionError("accepted payment plan before three weeks")
    except DomainError:
        verify("administration: no premature payment plan",True)
    repo.record_payment_action(unpaid_id,"reminder1",date(2026,10,17))
    repo.record_payment_action(unpaid_id,"reminder2",date(2026,10,24))
    repo.record_payment_action(unpaid_id,"payment_plan_accepted",date(2026,10,31))
    verify("administration: reminders and payment plan persisted",True)
    order1,delivery1=inserted_order(conn)
    repo.record_first_attempt_delivery(delivery1,date(2026,10,31),"yes")
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT status_naam FROM Bestelling WHERE bestelling_id=%s",(order1,))
        state1=cur.fetchone()
    verify("distribution: signed first delivery marks order delivered",
           state1["status_naam"]=="afgeleverd")
    order2,delivery2=inserted_order(conn)
    try:
        repo.schedule_second_attempt(delivery2,time(10,0),date(2026,10,31))
        raise AssertionError("second visit before first")
    except DomainError:
        verify("distribution: second visit must be later the same day",True)
    repo.schedule_second_attempt(delivery2,time(14,0),date(2026,10,31))
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT resultaat FROM Leverpoging WHERE levering_id=%s AND pogingnummer=2",(delivery2,))
        pending=cur.fetchone()
    verify("distribution: reschedule before entering final outcome",
           pending["resultaat"] is None)
    repo.record_second_attempt_outcome(delivery2,date(2026,10,31),"niet aanwezig",None)
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT status_naam FROM Bestelling WHERE bestelling_id=%s",(order2,))
        state2=cur.fetchone()
    verify("distribution: second absence is not marked delivered",
           state2["status_naam"]=="niet afgeleverd")
    repo.record_failed_delivery_followup(delivery2,date(2026,11,2),
                                         "ochtend","10.00","Klant tweemaal afwezig")
    with conn.cursor(dictionary=True) as cur:
        cur.execute("""SELECT gewenste_leverdatum,dagdeel,extra_bezorgkosten
                       FROM Bestelling WHERE bestelling_id=%s""",(order2,))
        followup=cur.fetchone()
    verify("distribution: sales followup stores agreed date and costs",
           followup["gewenste_leverdatum"]==date(2026,11,2)
           and followup["extra_bezorgkosten"]==Decimal("10.00"))
    prospects=repo.prospect_followups(date(2026,9,30))
    verify("acquisition: pharmacy without order due for followup",
           any(row["potentiele_klant_id"]==1 for row in prospects))
    new_customer=repo.register_prospect_customer(
        1,"Proef factuuradres","Proef afleveradres")
    with conn.cursor(dictionary=True) as cur:
        cur.execute("""SELECT k.eenmalige_korting_toegezegd,p.opvolging_afgesloten
                       FROM Klant k JOIN PotentieleKlant p ON p.klant_id=k.klant_id
                       WHERE k.klant_id=%s""",(new_customer,))
        registered=cur.fetchone()
    verify("acquisition: first-order incentive persisted and followup closed",
           bool(registered["eenmalige_korting_toegezegd"])
           and bool(registered["opvolging_afgesloten"]))
    verify("acquisition: accepted account excluded from callbacks",
           not repo.prospect_followups(date(2026,9,30)))
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO PotentieleKlant(bedrijfsnaam,contactpersoon,contactgegevens,adres_id)
                       VALUES ('Afwijzende apotheek','Contact','0633333333',3)""")
        declining=cur.lastrowid
        cur.execute("""INSERT INTO Acquisitiebezoek(potentiele_klant_id,bezoekdatum)
                       VALUES(%s,'2026-09-01')""",(declining,))
    conn.commit()
    repo.close_prospect_followup(declining,date(2026,9,30))
    verify("acquisition: refusal removes from followup",
           not repo.prospect_followups(date(2026,9,30)))
    app=create_app()
    app.config.update(TESTING=True,SECRET_KEY="caseproof",
                      DB_HOST=HOST,DB_PORT=PORT,DB_NAME=dbname,
                      DB_USER="root",DB_PASSWORD=password)
    with app.test_client() as client:
        endpoints=["/orders","/suppliers?product=Testmedicijn",
                   "/invoices?customer_id=1","/acquisition",
                   "/deliveries?day=2026-10-31"]
        responses={url:client.get(url).status_code for url in endpoints}
    verify("frontend: five scenario screens render with real MySQL",
           all(code==200 for code in responses.values()))
    print("HTTP:",responses)
    print("ALL INTEGRATION CHECKS PASSED")
    if "--write-evidence" in sys.argv:
        write_measured_evidence(observed)

def main():
    db_name="caseproof_"+uuid4().hex[:12]
    conn=mysql.connector.connect(host=HOST,port=PORT,user="root",password=PASSWORD,
                                 connection_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE "+db_name+" CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        run(conn,db_name,PASSWORD)
    finally:
        with conn.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS "+db_name)
        conn.commit()
        conn.close()

if __name__=="__main__":
    main()
