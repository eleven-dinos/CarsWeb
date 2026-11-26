import os

DATABASE_URL = os.environ.get("CARSWEB_DATABASE_URL", "sqlite:///./carsweb.db")
