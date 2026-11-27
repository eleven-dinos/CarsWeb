import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app import config
from app.models import UserSession, utc_now

password_hasher = PasswordHasher()

DUMMY_HASH = password_hasher.hash("not-a-real-password-used-for-timing")


def hash_password(password):
    return password_hasher.hash(password)


def check_password(password_hash, password):
    try:
        return password_hasher.verify(password_hash, password)
    except VerificationError:
        return False
    except InvalidHashError:
        return False


def waste_time_checking_password(password):
    check_password(DUMMY_HASH, password)


def new_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(first, second):
    if not isinstance(first, str) or not isinstance(second, str):
        return False
    return secrets.compare_digest(first.encode("utf-8"), second.encode("utf-8"))


def create_session(db, user):
    token = new_token()
    now = utc_now()
    session = UserSession(
        token_hash=hash_token(token),
        csrf_token=new_token(),
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=config.SESSION_MAX_HOURS),
        is_revoked=False,
    )
    db.add(session)
    db.commit()
    return token


def find_session(db, token):
    if not isinstance(token, str):
        return None
    if len(token) < 20 or len(token) > 100:
        return None

    session = db.query(UserSession).filter(UserSession.token_hash == hash_token(token)).first()
    if session is None:
        return None
    if session.is_revoked:
        return None

    now = utc_now()
    idle_limit = session.last_seen_at + timedelta(minutes=config.SESSION_IDLE_MINUTES)
    if session.expires_at <= now or idle_limit <= now:
        session.is_revoked = True
        db.commit()
        return None

    if not session.user.is_enabled:
        session.is_revoked = True
        db.commit()
        return None

    session.last_seen_at = now
    db.commit()
    return session


def revoke_all_sessions(db, user):
    sessions = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.is_revoked == False).all()
    for session in sessions:
        session.is_revoked = True
    db.commit()


def set_session_cookie(response, token):
    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response):
    response.delete_cookie(
        config.SESSION_COOKIE_NAME,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
