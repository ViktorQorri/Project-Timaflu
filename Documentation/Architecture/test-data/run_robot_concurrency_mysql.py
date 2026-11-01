"""Execute robot generation/completion concurrency tests against disposable MySQL.

Only runs in the explicitly isolated localhost test service, never production.
"""
import os
import sys
from pathlib import Path
from uuid import uuid4
import unittest
import mysql.connector

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "code" / "backend"


def schema_statements(path):
    lines = [x for x in path.read_text(encoding="utf-8").splitlines()
             if not x.lstrip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def run():
    if (os.getenv("TIMAFLU_TEST_ALLOW_RESET") != "isolated"
            or os.getenv("TIMAFLU_TEST_MYSQL_HOST") != "127.0.0.1"):
        raise RuntimeError("Only a dedicated localhost MySQL test service is allowed.")
    params = dict(
        host="127.0.0.1", port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        user=os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
        password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
    )
    name = "timaflu_robot_case_" + uuid4().hex[:12]
    admin = mysql.connector.connect(**params)
    try:
        with admin.cursor() as cursor:
            cursor.execute("CREATE DATABASE " + name + " CHARACTER SET utf8mb4")
        admin.commit()
        database = mysql.connector.connect(**params, database=name)
        try:
            with database.cursor() as cursor:
                for statement in schema_statements(ROOT / "code/database/schema.sql"):
                    cursor.execute(statement)
            database.commit()
        finally:
            database.close()
        os.environ.update(
            TIMAFLU_TEST_MYSQL="isolated",
            TIMAFLU_TEST_HOST="127.0.0.1",
            TIMAFLU_TEST_PORT=str(params["port"]),
            TIMAFLU_TEST_USER=params["user"],
            TIMAFLU_TEST_PASSWORD=params["password"],
            TIMAFLU_TEST_DATABASE=name,
        )
        sys.path.insert(0, str(BACKEND))
        suite = unittest.defaultTestLoader.loadTestsFromName("test_robot_concurrency_mysql")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful() or result.skipped:
            raise AssertionError("Robot concurrency test must run, not skip.")
        print("PASS: concurrent robot assignment and completion on disposable MySQL.")
    finally:
        with admin.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS " + name)
        admin.commit()
        admin.close()


if __name__ == "__main__":
    run()
