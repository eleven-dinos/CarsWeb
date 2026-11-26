from pathlib import Path

import jinja2
from fastapi.templating import Jinja2Templates

TEMPLATE_FOLDER = Path(__file__).parent / "templates"

environment = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_FOLDER), autoescape=True)

templates = Jinja2Templates(env=environment)
