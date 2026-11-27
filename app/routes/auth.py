from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import config
from app.auth import require_login
from app.database import get_db
from app.models import User, utc_now
from app.security import (
    check_password,
    clear_session_cookie,
    create_session,
    find_session,
    new_token,
    set_session_cookie,
    tokens_match,
    waste_time_checking_password,
)
from app.templates_setup import templates
from app.validation import clean, length_ok

router = APIRouter()

LOGIN_FAILED = "Login failed. Check your username and password, or try again later."
FORM_EXPIRED = "Your login form expired. Please try again."


def show_login(request, error=None, status_code=200):
    login_csrf_token = new_token()
    context = {"error": error, "login_csrf_token": login_csrf_token}
    response = templates.TemplateResponse(request, "login.html", context, status_code=status_code)
    response.set_cookie(
        config.LOGIN_CSRF_COOKIE_NAME,
        login_csrf_token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="strict",
        path="/login",
    )
    return response


@router.get("/login")
def login_page(request: Request):
    return show_login(request)


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    cookie_token = request.cookies.get(config.LOGIN_CSRF_COOKIE_NAME)
    if not tokens_match(form.get("csrf_token"), cookie_token):
        return show_login(request, FORM_EXPIRED, status_code=403)

    username = clean(form.get("username")).lower()
    password = form.get("password")
    if not isinstance(password, str):
        password = ""
    if len(password) > config.PASSWORD_MAX_LENGTH:
        password = ""

    user = None
    if length_ok(username, 3, 30) and password != "":
        user = db.query(User).filter(User.username == username).first()

    if user is None:
        waste_time_checking_password(password)
        return show_login(request, LOGIN_FAILED, status_code=401)

    now = utc_now()

    if user.locked_until is not None and user.locked_until > now:
        waste_time_checking_password(password)
        return show_login(request, LOGIN_FAILED, status_code=401)

    if not user.is_enabled:
        waste_time_checking_password(password)
        return show_login(request, LOGIN_FAILED, status_code=401)

    if not check_password(user.password_hash, password):
        user.failed_logins = user.failed_logins + 1
        if user.failed_logins >= config.MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=config.LOCKOUT_MINUTES)
            user.failed_logins = 0
        db.commit()
        return show_login(request, LOGIN_FAILED, status_code=401)

    user.failed_logins = 0
    user.locked_until = None
    db.commit()

    old_session = find_session(db, request.cookies.get(config.SESSION_COOKIE_NAME))
    if old_session is not None:
        old_session.is_revoked = True
        db.commit()

    token = create_session(db, user)
    response = RedirectResponse("/vehicles", status_code=303)
    set_session_cookie(response, token)
    response.delete_cookie(config.LOGIN_CSRF_COOKIE_NAME, path="/login")
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), current_user=Depends(require_login)):
    session = request.state.session
    session.is_revoked = True
    db.commit()

    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response
