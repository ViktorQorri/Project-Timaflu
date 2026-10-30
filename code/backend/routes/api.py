from flask import Blueprint, jsonify, request

from db import get_connection
from repositories.health_repository import HealthRepository
from services.health_service import HealthService
from repositories.robot_order_repository import RobotOrderRepository
from services.robot_order_service import RobotOrderService

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    """Tell a robot whether the backend and the database are up.

    Returns:
        JSON with the status, for example {"status": "ok", "database": true}.
    """
    health_service = HealthService(HealthRepository(get_connection()))
    return jsonify(status="ok", database=health_service.database_is_reachable())

def _robot_service():
    return RobotOrderService(RobotOrderRepository(get_connection()))


@api.get("/robots/<int:robot_id>/next")
def next_robot_order(robot_id):
    """Return an existing unfinished sub-order assigned to this robot's aisle."""
    result = _robot_service().next_order(robot_id, request.args.get("aisle"))
    return jsonify(result)


@api.post("/robots/<int:robot_id>/complete")
def complete_robot_order(robot_id):
    """Persist completion after the robot has registered its collection bins."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Verwacht een JSON-object."), 400
    result = _robot_service().complete(
        robot_id, payload.get("aisle"), payload.get("suborder_id")
    )
    return jsonify(result)
