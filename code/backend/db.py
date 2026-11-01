import mysql.connector
from flask import current_app, g


def connection_options(config):
    """Build MySQL connection settings without weakening certificate verification."""
    options = {
        "host": config["DB_HOST"],
        "port": config["DB_PORT"],
        "database": config["DB_NAME"],
        "user": config["DB_USER"],
        "password": config["DB_PASSWORD"],
        "connection_timeout": 5,
    }
    ca_path = str(config.get("DB_SSL_CA") or "").strip()
    require_tls = bool(config.get("DB_REQUIRE_TLS", False))
    if require_tls and not ca_path:
        raise ValueError("DB_REQUIRE_TLS=1 vereist DB_SSL_CA met een vertrouwd certificaat.")
    if ca_path:
        from pathlib import Path
        if not Path(ca_path).is_file():
            raise ValueError("DB_SSL_CA verwijst niet naar een bestaand bestand.")
        options.update(
            ssl_ca=ca_path,
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )
    return options


def get_connection():
    """Return the database connection for the current request, opening it on first use.

    Returns:
        A mysql.connector connection. Uncommitted changes are discarded when it closes,
        so repository methods that write must call commit().
    """
    if "db" not in g:
        g.db = mysql.connector.connect(**connection_options(current_app.config))
    return g.db


def close_connection(exception=None):
    """Close the connection at the end of the request, if one was opened.

    Args:
        exception: The error that ended the request, or None. Passed in by Flask.
    """
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
