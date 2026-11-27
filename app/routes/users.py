from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.auth import require_admin
from app.database import get_db
from app.models import ROLES, User, utc_now
from app.security import hash_password, revoke_all_sessions
from app.templates_setup import templates
from app.validation import check_new_password, check_username, clean

router = APIRouter()

MESSAGES = {
    "created": "User created.",
    "disabled": "User disabled and logged out everywhere.",
    "enabled": "User enabled.",
    "self": "You cannot disable your own account.",
}

USERNAME_TAKEN = "This username is already taken."


def get_user_or_404(db, user_id):
    if user_id < 1 or user_id > 999999999:
        raise HTTPException(status_code=404)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404)
    return user


def show_form(request, data, errors, status_code=200):
    context = {"data": data, "errors": errors, "roles": ROLES}
    return templates.TemplateResponse(request, "users/form.html", context, status_code=status_code)


@router.get("/users")
def list_users(request: Request, done: str = "", db: Session = Depends(get_db), current_user=Depends(require_admin)):
    users = db.query(User).order_by(User.username).all()
    context = {"users": users, "message": MESSAGES.get(done), "now": utc_now()}
    return templates.TemplateResponse(request, "users/list.html", context)


@router.get("/users/new")
def new_user_form(request: Request, current_user=Depends(require_admin)):
    return show_form(request, {"role": "staff"}, {})


@router.post("/users/new")
async def create_user(request: Request, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    form = await request.form()
    data = {}
    data["username"] = clean(form.get("username")).lower()
    data["role"] = clean(form.get("role"))

    password = form.get("password")
    confirm = form.get("confirm_password")
    if not isinstance(password, str):
        password = ""
    if not isinstance(confirm, str):
        confirm = ""

    errors = {}
    username_error = check_username(data["username"])
    if username_error is not None:
        errors["username"] = username_error
    elif db.query(User).filter(User.username == data["username"]).first() is not None:
        errors["username"] = USERNAME_TAKEN

    if data["role"] not in ROLES:
        errors["role"] = "Choose a valid role."

    password_error = check_new_password(password, confirm, data["username"], config.PASSWORD_MIN_LENGTH, config.PASSWORD_MAX_LENGTH)
    if password_error is not None:
        errors["password"] = password_error

    if errors:
        return show_form(request, data, errors, status_code=400)

    user = User(username=data["username"], password_hash=hash_password(password), role=data["role"], is_enabled=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors["username"] = USERNAME_TAKEN
        return show_form(request, data, errors, status_code=400)

    return RedirectResponse("/users?done=created", status_code=303)


@router.post("/users/{user_id}/disable")
def disable_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    user = get_user_or_404(db, user_id)
    if user.id == current_user.id:
        return RedirectResponse("/users?done=self", status_code=303)

    user.is_enabled = False
    db.commit()
    revoke_all_sessions(db, user)
    return RedirectResponse("/users?done=disabled", status_code=303)


@router.post("/users/{user_id}/enable")
def enable_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    user = get_user_or_404(db, user_id)
    user.is_enabled = True
    db.commit()
    return RedirectResponse("/users?done=enabled", status_code=303)
