"""Equipment catalogue endpoints for the add-new-equipment story."""

from flask import Blueprint, request

# Reuse the existing equipment route handler: same bearer-token check,
# authenticated client and EquipmentError-to-JSON mapping.
from app.routes.equipment_reservations import _handle
from app.services import add_new_equipment_service as service

add_new_equipment_bp = Blueprint("add_new_equipment", __name__, url_prefix="/api/equipment-catalogue")


@add_new_equipment_bp.get("")
def list_catalogue():
    return _handle(service.list_catalogue)


@add_new_equipment_bp.post("")
def add_equipment():
    return _handle(lambda c, u: service.add_equipment(c, u, request.get_json(silent=True)))