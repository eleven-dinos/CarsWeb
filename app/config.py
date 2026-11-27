import os

DATABASE_URL = os.environ.get("CARSWEB_DATABASE_URL", "sqlite:///./carsweb.db")

COOKIE_SECURE = True
if os.environ.get("CARSWEB_COOKIE_SECURE", "true").lower() == "false":
    COOKIE_SECURE = False

SESSION_COOKIE_NAME = "carsweb_session"
LOGIN_CSRF_COOKIE_NAME = "carsweb_login_csrf"
SESSION_IDLE_MINUTES = 15
SESSION_MAX_HOURS = 8

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
