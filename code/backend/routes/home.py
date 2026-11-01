from flask import Blueprint, render_template
from mysql.connector import Error as DatabaseError

from db import get_connection
from repositories.health_repository import HealthRepository
from services.health_service import HealthService

home = Blueprint("home", __name__)


@home.get("/")
def index():
    """Show the start page with the processes and the database status."""
    try:
        health_service = HealthService(HealthRepository(get_connection()))
        database_ok = health_service.database_is_reachable()
    except DatabaseError:
        database_ok = False
    return render_template("index.html", database_ok=database_ok)
