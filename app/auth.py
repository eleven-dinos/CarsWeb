from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.security import find_session, tokens_match


async def require_login(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    session = find_session(db, token)
    if session is None:
        raise HTTPException(status_code=401)

    if request.method == "POST":
        form = await request.form()
        if not tokens_match(form.get("csrf_token"), session.csrf_token):
            raise HTTPException(status_code=403)

    request.state.session = session
    request.state.user = session.user
    request.state.csrf_token = session.csrf_token
    return session.user


def require_staff(current_user=Depends(require_login)):
    if current_user.role != "admin" and current_user.role != "staff":
        raise HTTPException(status_code=403)
    return current_user


def require_admin(current_user=Depends(require_login)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403)
    return current_user
