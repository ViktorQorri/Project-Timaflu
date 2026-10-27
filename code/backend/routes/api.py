from flask import Blueprint, jsonify

from db import get_connection
from repositories.health_repository import HealthRepository
from services.health_service import HealthService

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    """Tell a robot whether the backend and the database are up.

    Returns:
        JSON with the status, for example {"status": "ok", "database": true}.
    """
    health_service = HealthService(HealthRepository(get_connection()))
    return jsonify(status="ok", database=health_service.database_is_reachable())
