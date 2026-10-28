from flask import Blueprint, render_template

from db import get_connection
from repositories.health_repository import HealthRepository
from services.health_service import HealthService

home = Blueprint("home", __name__)


@home.get("/")
def index():
    """Show the start page with the processes and the database status."""
    health_service = HealthService(HealthRepository(get_connection()))
    return render_template("index.html", database_ok=health_service.database_is_reachable())
