"""Read-only proof that a hosted MySQL database matches the Timaflu project.

Normal runs reject localhost and require certificate-verified TLS. The
--allow-local flag is only for isolated development testing and explicitly
does NOT prove that a database is online.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "backend"))

from config import Config
from db import connection_options
from validate_eer_schema import sql_columns

# Useful minimum representative records, NOT thresholds stated by the school.
MIN_ROWS = {
    "klant": 1,
    "product": 2,
    "leverancier": 2,
    "leveranciersaanbod": 2,
    "bestelling": 2,
    "bestelregel": 2,
    "magazijnlocatie": 1,
    "levering": 1,
    "leveringregel": 1,
    "factuur": 1,
    "potentieleklant": 1,
    "acquisitiebezoek": 1,
}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "db", "host.docker.internal"}


def verify(allow_local: bool = False) -> dict:
    hostname = str(Config.DB_HOST or "").strip().lower()
    if not allow_local:
        if not hostname or hostname in LOCAL_HOSTS:
            raise ValueError("Online bewijs vereist een externe databasehost.")
        if not Config.DB_REQUIRE_TLS or not Config.DB_SSL_CA:
            raise ValueError("Online controle vereist DB_REQUIRE_TLS=1 en een geldig DB_SSL_CA-bestand.")
        if not Config.DB_PASSWORD:
            raise ValueError("Online controle vereist een databasewachtwoord.")

    conn = mysql.connector.connect(**connection_options(vars(Config)))
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
            tls_row = cursor.fetchone()
            cipher = tls_row.get("Value", "") if tls_row else ""
            if not allow_local and not cipher:
                raise ValueError("De databaseverbinding is niet versleuteld.")

            cursor.execute("SELECT VERSION() AS version, UTC_TIMESTAMP() AS checked_at")
            server = cursor.fetchone()

            cursor.execute(
                """SELECT TABLE_NAME, TABLE_TYPE
                   FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s""",
                (Config.DB_NAME,),
            )
            discovered = {
                row["TABLE_NAME"].lower(): (row["TABLE_NAME"], row["TABLE_TYPE"])
                for row in cursor.fetchall()
            }
            expected = sql_columns()
            actual_tables = {name for name, (_, kind) in discovered.items() if kind == "BASE TABLE"}
            missing_tables = sorted(set(expected) - actual_tables)
            extra_tables = sorted(actual_tables - set(expected))

            cursor.execute(
                """SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE,
                          CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                   FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = %s""",
                (Config.DB_NAME,),
            )
            columns: dict[str, dict] = {}
            for column in cursor.fetchall():
                table = column["TABLE_NAME"].lower()
                columns.setdefault(table, {})[column["COLUMN_NAME"].lower()] = column

            differences = []
            for table in sorted(set(expected) & actual_tables):
                wanted = expected[table]
                found = columns.get(table, {})
                for name in sorted(wanted.keys() - found.keys()):
                    differences.append(f"{table}.{name} ontbreekt")
                for name in sorted(found.keys() - wanted.keys()):
                    differences.append(f"{table}.{name} is extra")
                for name in sorted(wanted.keys() & found.keys()):
                    expected_type = wanted[name]["type"].replace("_f", "")
                    if found[name]["DATA_TYPE"].lower() != expected_type:
                        differences.append(f"{table}.{name}: ander datatype")
                    if (found[name]["IS_NULLABLE"] == "YES") != wanted[name]["nullable"]:
                        differences.append(f"{table}.{name}: andere nullability")
                    expected_length = wanted[name]["length"]
                    if (expected_length is not None
                            and int(found[name]["CHARACTER_MAXIMUM_LENGTH"] or 0) != expected_length):
                        differences.append(f"{table}.{name}: andere lengte")

            schema = (ROOT / "code" / "database" / "schema.sql").read_text(encoding="utf-8")
            schema = re.sub(r"(?m)^\s*--.*$", "", schema)
            expected_foreign_keys = len(re.findall(r"\bFOREIGN\s+KEY\s*\(", schema, re.I))
            cursor.execute(
                """SELECT COUNT(*) AS number FROM (
                    SELECT TABLE_NAME, CONSTRAINT_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
                    GROUP BY TABLE_NAME, CONSTRAINT_NAME
                ) AS foreign_keys""",
                (Config.DB_NAME,),
            )
            foreign_keys = int(cursor.fetchone()["number"])
            cursor.execute(
                """SELECT COUNT(DISTINCT TABLE_NAME) AS number
                   FROM information_schema.TABLE_CONSTRAINTS
                   WHERE TABLE_SCHEMA = %s AND CONSTRAINT_TYPE = 'PRIMARY KEY'""",
                (Config.DB_NAME,),
            )
            primary_keys = int(cursor.fetchone()["number"])

            if discovered.get("factuuroverzicht", (None, None))[1] != "VIEW":
                differences.append("FactuurOverzicht-view ontbreekt")
            if foreign_keys != expected_foreign_keys:
                differences.append("Aantal foreign keys verschilt van schema.sql")
            if primary_keys != len(expected):
                differences.append("Niet iedere tabel heeft een primary key")

            counts = {}
            for table in sorted(set(expected) & actual_tables):
                # The physical table name comes only from information_schema,
                # restricted to names present in our checked-in schema.
                original_name = discovered[table][0]
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", original_name):
                    raise ValueError("Onverwachte tabelnaam in database.")
                cursor.execute(f"SELECT COUNT(*) AS number FROM {original_name}")
                counts[table] = int(cursor.fetchone()["number"])

            shortfalls = {
                table: {"gevonden": counts.get(table, 0), "minimum": minimum}
                for table, minimum in MIN_ROWS.items()
                if counts.get(table, 0) < minimum
            }

            report = {
                "controle": "LOKALE TEST, GEEN ONLINE BEWIJS" if allow_local else "EXTERNE DATABASECONTROLE",
                "tijdstip_utc": server["checked_at"].isoformat(),
                "mysql_versie": server["version"],
                "tls_actief": bool(cipher),
                "tabellen": len(actual_tables),
                "primaire_sleutels": primary_keys,
                "foreign_keys": foreign_keys,
                "rijen_per_tabel": dict(sorted(counts.items())),
                "ontbrekende_tabellen": missing_tables,
                "extra_tabellen": extra_tables,
                "schema_afwijkingen": differences,
                "onvoldoende_voorbeelddata": shortfalls,
            }
            if missing_tables or extra_tables or differences or shortfalls:
                raise ValueError("Schema of demonstratiegegevens onvoldoende: " + json.dumps({
                    "ontbrekende_tabellen": missing_tables,
                    "extra_tabellen": extra_tables,
                    "schema_afwijkingen": differences[:20],
                    "onvoldoende_voorbeelddata": shortfalls,
                }, ensure_ascii=False))
            return report
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", type=Path, help="Bewaar enkel metadata en aantallen.")
    parser.add_argument("--allow-local", action="store_true", help="Uitsluitend development; geen online bewijs.")
    args = parser.parse_args()
    try:
        result = verify(allow_local=args.allow_local)
    except (ValueError, mysql.connector.Error) as exc:
        if isinstance(exc, mysql.connector.Error):
            raise SystemExit(f"FAIL: MySQL-fout {exc.errno}; controleer verbinding, TLS en SELECT-rechten.") from None
        raise SystemExit(f"FAIL: {exc}") from None

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
