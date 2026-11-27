from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_admin, require_staff
from app.database import get_db
from app.models import Client, Vehicle
from app.templates_setup import templates
from app.validation import validate_client

router = APIRouter()

MESSAGES = {
    "created": "Client added.",
    "updated": "Client updated.",
    "deleted": "Client deleted.",
}

IN_USE_MESSAGE = "This client is linked to one or more vehicles and cannot be deleted."


def get_client_or_404(db, client_id):
    if client_id < 1 or client_id > 999999999:
        raise HTTPException(status_code=404)
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404)
    return client


def show_form(request, data, errors, client_id=None, status_code=200):
    context = {"data": data, "errors": errors, "client_id": client_id}
    return templates.TemplateResponse(request, "clients/form.html", context, status_code=status_code)


def show_delete_page(request, client, error=None, status_code=200):
    context = {
        "title": "Delete client",
        "item": client.name,
        "action": "/clients/" + str(client.id) + "/delete",
        "cancel": "/clients",
        "error": error,
    }
    return templates.TemplateResponse(request, "confirm_delete.html", context, status_code=status_code)


@router.get("/clients")
def list_clients(request: Request, done: str = "", db: Session = Depends(get_db), current_user=Depends(require_staff)):
    clients = db.query(Client).order_by(Client.name).all()
    context = {"clients": clients, "message": MESSAGES.get(done)}
    return templates.TemplateResponse(request, "clients/list.html", context)


@router.get("/clients/new")
def new_client_form(request: Request, current_user=Depends(require_staff)):
    return show_form(request, {}, {})


@router.post("/clients/new")
async def create_client(request: Request, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    form = await request.form()
    data, errors = validate_client(form)
    if errors:
        return show_form(request, data, errors, status_code=400)

    client = Client(name=data["name"], email=data["email"], country=data["country"])
    db.add(client)
    db.commit()
    return RedirectResponse("/clients?done=created", status_code=303)


@router.get("/clients/{client_id}/edit")
def edit_client_form(request: Request, client_id: int, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    client = get_client_or_404(db, client_id)
    data = {"name": client.name, "email": client.email, "country": client.country}
    return show_form(request, data, {}, client_id=client.id)


@router.post("/clients/{client_id}/edit")
async def update_client(request: Request, client_id: int, db: Session = Depends(get_db), current_user=Depends(require_staff)):
    client = get_client_or_404(db, client_id)
    form = await request.form()
    data, errors = validate_client(form)
    if errors:
        return show_form(request, data, errors, client_id=client.id, status_code=400)

    client.name = data["name"]
    client.email = data["email"]
    client.country = data["country"]
    db.commit()
    return RedirectResponse("/clients?done=updated", status_code=303)


@router.get("/clients/{client_id}/delete")
def delete_client_page(request: Request, client_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    client = get_client_or_404(db, client_id)
    return show_delete_page(request, client)


@router.post("/clients/{client_id}/delete")
def delete_client(request: Request, client_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    client = get_client_or_404(db, client_id)
    vehicle_count = db.query(Vehicle).filter(Vehicle.client_id == client.id).count()
    if vehicle_count > 0:
        return show_delete_page(request, client, error=IN_USE_MESSAGE, status_code=409)

    db.delete(client)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return show_delete_page(request, client, error=IN_USE_MESSAGE, status_code=409)

    return RedirectResponse("/clients?done=deleted", status_code=303)
