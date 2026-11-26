from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.models import create_tables
from app.routes import clients, vehicles, yards

STATIC_FOLDER = Path(__file__).parent / "static"

create_tables()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")

app.include_router(vehicles.router)
app.include_router(clients.router)
app.include_router(yards.router)


@app.get("/")
def home():
    return RedirectResponse("/vehicles", status_code=303)
