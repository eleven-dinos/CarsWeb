from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models import create_tables
from app.routes import auth, clients, users, vehicles, yards
from app.templates_setup import templates

STATIC_FOLDER = Path(__file__).parent / "static"

ERROR_MESSAGES = {
    403: "You do not have permission to do that.",
    404: "The page you asked for could not be found.",
    405: "That action is not allowed.",
}

create_tables()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")

app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(clients.router)
app.include_router(yards.router)
app.include_router(users.router)


@app.exception_handler(StarletteHTTPException)
def handle_http_error(request: Request, error: StarletteHTTPException):
    if error.status_code == 401:
        return RedirectResponse("/login", status_code=303)

    message = ERROR_MESSAGES.get(error.status_code, "Something went wrong. Please try again.")
    context = {"error_message": message}
    return templates.TemplateResponse(request, "error.html", context, status_code=error.status_code)


@app.get("/")
def home():
    return RedirectResponse("/vehicles", status_code=303)
