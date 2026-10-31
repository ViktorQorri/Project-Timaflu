"""Verify case additions can be migrated from PR #94's prior schema.

Uses a newly created database in the local disposable MySQL 8.4 container.
"""
from pathlib import Path
from uuid import uuid4
import subprocess
import mysql.connector
from run_caseproof_mysql import HOST, PORT, PASSWORD, ROOT, sql_statements

BASE="d936cd3917c3c00b1b0bc652107a54c8d9172cb6"

def run_text(conn,contents):
    statements="\n".join(x for x in contents.splitlines() if not x.strip().startswith("--"))
    with conn.cursor() as cur:
        for statement in statements.split(";"):
            if statement.strip(): cur.execute(statement.strip())
    conn.commit()

def old_file(path):
    command=["git","-C",str(ROOT),"show",BASE+":"+path]
    return subprocess.run(command,check=True,capture_output=True,text=True,
                          encoding="utf-8").stdout

def main():
    name="caseproofmigration_"+uuid4().hex[:10]
    conn=mysql.connector.connect(host=HOST,port=PORT,user="root",
                                 password=PASSWORD,connection_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE "+name+" CHARACTER SET utf8mb4")
            cur.execute("USE "+name)
        conn.commit()
        run_text(conn,old_file("code/database/schema.sql"))
        for file in ("2026_10_31_acquisition_followup.sql",
                     "2026_10_31_failed_delivery_status.sql"):
            with conn.cursor() as cur:
                for statement in sql_statements(ROOT/"code/database/migrations"/file):
                    cur.execute(statement)
            conn.commit()
            print("MIGRATION APPLIED",file)
        run_text(conn,old_file("Documentation/Architecture/test-data/fixtures_assessed.sql"))
        with conn.cursor(dictionary=True) as cur:
            for table,column in (("Klant","eenmalige_korting_toegezegd"),
                                 ("PotentieleKlant","opvolging_afgesloten")):
                cur.execute(
                    """SELECT COUNT(*) AS num FROM information_schema.COLUMNS
                       WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
                         AND IS_NULLABLE='NO'""",(name,table,column))
                assert cur.fetchone()["num"]==1,(table,column)
                print("MIGRATED COLUMN",table,column)
            cur.execute("SELECT COUNT(*) AS num FROM OrderStatus WHERE naam='niet afgeleverd'")
            assert cur.fetchone()["num"]==1
            cur.execute("SELECT COUNT(*) AS num FROM Klant")
            assert cur.fetchone()["num"]>=1
            print("MIGRATION AND LEGACY DATA CHECKS PASSED")
    finally:
        with conn.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS "+name)
        conn.commit()
        conn.close()

if __name__=="__main__":
    main()
