from flask import Blueprint, jsonify, request

from db import get_connection
from domain.errors import DomainError
from repositories.health_repository import HealthRepository
from repositories.picking_bin_repository import PickingBinRepository
from services.health_service import HealthService
from services.picking_bin_service import PickingBinService

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    """Tell a robot whether the backend and the database are up.

    Returns:
        JSON with the status, for example {"status": "ok", "database": true}.
    """
    health_service = HealthService(HealthRepository(get_connection()))
    return jsonify(status="ok", database=health_service.database_is_reachable())


@api.post("/picking-bins")
def register_picking_bin():
    """Link the code of a picking bin a robot just scanned to the sub-order it is collecting.

    Expects JSON with the robot's aisle, the sub-order and the bin code, for example
    {"aisle": "B", "sub_order_id": 7, "bin_code": "VB-0001"}. A rejected bin answers
    400, 404 or 409 with {"error": "..."} through the error handlers in app.py.

    Returns:
        JSON with the registered link, for example
        {"accepted": true, "bin_code": "VB-0001", "order_id": 3, "sub_order_id": 7, "aisle": "B"}.
    """
    message = request.get_json(silent=True)
    if not isinstance(message, dict):
        raise DomainError("Stuur een JSON-object met aisle, sub_order_id en bin_code.")
    service = PickingBinService(PickingBinRepository(get_connection()))
    registered = service.register(message.get("bin_code"), message.get("sub_order_id"), message.get("aisle"))
    return jsonify(
        accepted=True,
        bin_code=registered["unieke_code"],
        order_id=registered["bestelling_id"],
        sub_order_id=registered["deelorder_id"],
        aisle=registered["gang"],
    )
