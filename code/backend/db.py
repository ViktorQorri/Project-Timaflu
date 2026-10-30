import mysql.connector
from flask import current_app, g


def get_connection():
    """Return the database connection for the current request, opening it on first use.

    Returns:
        A mysql.connector connection. Uncommitted changes are discarded when it closes,
        so repository methods that write must call commit().
    """
    if "db" not in g:
        config = current_app.config
        g.db = mysql.connector.connect(
            host=config["DB_HOST"],
            port=config["DB_PORT"],
            database=config["DB_NAME"],
            user=config["DB_USER"],
            password=config["DB_PASSWORD"],
            connection_timeout=5,
        )
    return g.db


def close_connection(exception=None):
    """Close the connection at the end of the request, if one was opened.

    Args:
        exception: The error that ended the request, or None. Passed in by Flask.
    """
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
