from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_admin, require_login, require_staff
from app.database import get_db
from app.models import VEHICLE_STATUSES, Client, Vehicle, Yard
from app.templates_setup import templates
from app.validation import price_to_cents, validate_vehicle

router = APIRouter()

MESSAGES = {
    "created": "Vehicle added.",
    "updated": "Vehicle updated.",
    "deleted": "Vehicle deleted.",
}

SAVE_FAILED = "The vehicle could not be saved. Check the stock and chassis numbers are unique."


def get_vehicle_or_404(db, vehicle_id):
    if vehicle_id < 1 or vehicle_id > 999999999:
        raise HTTPException(status_code=404)
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404)
    return vehicle


def show_form(request, db, data, errors, vehicle_id=None, status_code=200):
    clients = db.query(Client).order_by(Client.name).all()
    yards = db.query(Yard).order_by(Yard.name).all()
    context = {
        "data": data,
        "errors": errors,
        "vehicle_id": vehicle_id,
        "clients": clients,
        "yards": yards,
        "statuses": VEHICLE_STATUSES,
    }
    return templates.TemplateResponse(request, "vehicles/form.html", context, status_code=status_code)


def copy_data_to_vehicle(data, vehicle):
    vehicle.stock_number = data["stock_number"]
    vehicle.chassis_number = data["chassis_number"]
    vehicle.make = data["make"]
    vehicle.model = data["model"]
    vehicle.year = int(data["year"])
    vehicle.price_cents = price_to_cents(data["price"])
    vehicle.status = data["status"]
    vehicle.yard_id = int(data["yard_id"])
    if data["client_id"] == "":
        vehicle.client_id = None
    else:
        vehicle.client_id = int(data["client_id"])


@router.get("/vehicles")
def list_vehicles(request: Request, done: str = "", db: Session = Depends(get_db), current_user=Depends(require_login)):
    vehicles = db.query(Vehicle).order_by(Vehicle.stock_number).all()
    context = {"vehicles": vehicles, "message": MESSAGES.get(done)}
    return templates.TemplateResponse(request, "vehicles/list.html", context)


@router.get("/vehicles/new")
def new_vehicle_form(request: Request, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    data = {"status": "Available"}
    return show_form(request, db, data, {})


@router.post("/vehicles/new")
async def create_vehicle(request: Request, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    form = await request.form()
    data, errors = validate_vehicle(form, db)
    if errors:
        return show_form(request, db, data, errors, status_code=400)

    vehicle = Vehicle()
    copy_data_to_vehicle(data, vehicle)
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors["form"] = SAVE_FAILED
        return show_form(request, db, data, errors, status_code=400)

    return RedirectResponse("/vehicles?done=created", status_code=303)


@router.get("/vehicles/{vehicle_id}/edit")
def edit_vehicle_form(request: Request, vehicle_id: int, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    data = {}
    data["stock_number"] = vehicle.stock_number
    data["chassis_number"] = vehicle.chassis_number
    data["make"] = vehicle.make
    data["model"] = vehicle.model
    data["year"] = str(vehicle.year)
    data["price"] = vehicle.price_text()
    data["status"] = vehicle.status
    data["yard_id"] = str(vehicle.yard_id)
    if vehicle.client_id is None:
        data["client_id"] = ""
    else:
        data["client_id"] = str(vehicle.client_id)
    return show_form(request, db, data, {}, vehicle_id=vehicle.id)


@router.post("/vehicles/{vehicle_id}/edit")
async def update_vehicle(request: Request, vehicle_id: int, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    form = await request.form()
    data, errors = validate_vehicle(form, db, vehicle_id=vehicle.id)
    if errors:
        return show_form(request, db, data, errors, vehicle_id=vehicle.id, status_code=400)

    copy_data_to_vehicle(data, vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors["form"] = SAVE_FAILED
        return show_form(request, db, data, errors, vehicle_id=vehicle_id, status_code=400)

    return RedirectResponse("/vehicles?done=updated", status_code=303)


@router.get("/vehicles/{vehicle_id}/delete")
def delete_vehicle_page(request: Request, vehicle_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    context = {
        "title": "Delete vehicle",
        "item": vehicle.stock_number + " - " + vehicle.make + " " + vehicle.model,
        "action": "/vehicles/" + str(vehicle.id) + "/delete",
        "cancel": "/vehicles",
    }
    return templates.TemplateResponse(request, "confirm_delete.html", context)


@router.post("/vehicles/{vehicle_id}/delete")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    vehicle = get_vehicle_or_404(db, vehicle_id)
    db.delete(vehicle)
    db.commit()
    return RedirectResponse("/vehicles?done=deleted", status_code=303)
