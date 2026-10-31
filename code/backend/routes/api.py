from flask import Blueprint, jsonify, request

from db import get_connection
from domain.errors import DomainError
from repositories.health_repository import HealthRepository
from repositories.picking_bin_repository import PickingBinRepository
from repositories.robot_order_repository import RobotOrderRepository
from services.health_service import HealthService
from services.picking_bin_service import PickingBinService
from services.robot_order_service import RobotOrderService


api = Blueprint("api", __name__)


def _robot_service():
    return RobotOrderService(RobotOrderRepository(get_connection()))


@api.get("/health")
def health():
    """Tell a robot whether the backend and the database are up."""
    health_service = HealthService(HealthRepository(get_connection()))
    return jsonify(status="ok", database=health_service.database_is_reachable())


@api.post("/picking-bins")
def register_picking_bin():
    """Link a scanned picking bin to the sub-order collected by a robot."""
    message = request.get_json(silent=True)
    if not isinstance(message, dict):
        raise DomainError("Stuur een JSON-object met aisle, sub_order_id en bin_code.")
    service = PickingBinService(PickingBinRepository(get_connection()))
    registered = service.register(
        message.get("bin_code"),
        message.get("sub_order_id"),
        message.get("aisle"),
    )
    return jsonify(
        accepted=True,
        bin_code=registered["unieke_code"],
        order_id=registered["bestelling_id"],
        sub_order_id=registered["deelorder_id"],
        aisle=registered["gang"],
    )


@api.get("/robots/<int:robot_id>/next")
def next_robot_order(robot_id):
    """Return an unfinished sub-order assigned to the robot's aisle."""
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


@api.post("/orders/<int:order_id>/suborders")
def generate_robot_suborders(order_id):
    """Generate aisle-specific partial orders from the existing stock reservation."""
    return jsonify(suborders=_robot_service().generate_suborders(order_id)), 201
