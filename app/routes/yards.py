from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_admin, require_staff
from app.database import get_db
from app.models import Vehicle, Yard
from app.templates_setup import templates
from app.validation import validate_yard

router = APIRouter()

MESSAGES = {
    "created": "Yard added.",
    "updated": "Yard updated.",
    "deleted": "Yard deleted.",
}

IN_USE_MESSAGE = "This yard still holds one or more vehicles and cannot be deleted."
NAME_TAKEN = "A yard with this name already exists."


def get_yard_or_404(db, yard_id):
    if yard_id < 1 or yard_id > 999999999:
        raise HTTPException(status_code=404)
    yard = db.get(Yard, yard_id)
    if yard is None:
        raise HTTPException(status_code=404)
    return yard


def show_form(request, data, errors, yard_id=None, status_code=200):
    context = {"data": data, "errors": errors, "yard_id": yard_id}
    return templates.TemplateResponse(request, "yards/form.html", context, status_code=status_code)


def show_delete_page(request, yard, error=None, status_code=200):
    context = {
        "title": "Delete yard",
        "item": yard.name,
        "action": "/yards/" + str(yard.id) + "/delete",
        "cancel": "/yards",
        "error": error,
    }
    return templates.TemplateResponse(request, "confirm_delete.html", context, status_code=status_code)


@router.get("/yards")
def list_yards(request: Request, done: str = "", db: Session = Depends(get_db), current_user=Depends(require_staff)):
    yards = db.query(Yard).order_by(Yard.name).all()
    context = {"yards": yards, "message": MESSAGES.get(done)}
    return templates.TemplateResponse(request, "yards/list.html", context)


@router.get("/yards/new")
def new_yard_form(request: Request, current_user=Depends(require_staff)):
    return show_form(request, {}, {})


@router.post("/yards/new")
async def create_yard(request: Request, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    form = await request.form()
    data, errors = validate_yard(form, db)
    if errors:
        return show_form(request, data, errors, status_code=400)

    yard = Yard(name=data["name"], location=data["location"])
    db.add(yard)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors["name"] = NAME_TAKEN
        return show_form(request, data, errors, status_code=400)

    return RedirectResponse("/yards?done=created", status_code=303)


@router.get("/yards/{yard_id}/edit")
def edit_yard_form(request: Request, yard_id: int, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    yard = get_yard_or_404(db, yard_id)
    data = {"name": yard.name, "location": yard.location}
    return show_form(request, data, {}, yard_id=yard.id)


@router.post("/yards/{yard_id}/edit")
async def update_yard(request: Request, yard_id: int, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    yard = get_yard_or_404(db, yard_id)
    form = await request.form()
    data, errors = validate_yard(form, db, yard_id=yard.id)
    if errors:
        return show_form(request, data, errors, yard_id=yard.id, status_code=400)

    yard.name = data["name"]
    yard.location = data["location"]
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors["name"] = NAME_TAKEN
        return show_form(request, data, errors, yard_id=yard_id, status_code=400)

    return RedirectResponse("/yards?done=updated", status_code=303)


@router.get("/yards/{yard_id}/delete")
def delete_yard_page(request: Request, yard_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    yard = get_yard_or_404(db, yard_id)
    return show_delete_page(request, yard)


@router.post("/yards/{yard_id}/delete")
def delete_yard(request: Request, yard_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    yard = get_yard_or_404(db, yard_id)
    vehicle_count = db.query(Vehicle).filter(Vehicle.yard_id == yard.id).count()
    if vehicle_count > 0:
        return show_delete_page(request, yard, error=IN_USE_MESSAGE, status_code=409)

    db.delete(yard)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return show_delete_page(request, yard, error=IN_USE_MESSAGE, status_code=409)

    return RedirectResponse("/yards?done=deleted", status_code=303)
