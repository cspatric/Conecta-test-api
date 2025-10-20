import os
import datetime
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SQLITE_PATH = os.path.join(PROJECT_ROOT, "instance", "app.db")
DEFAULT_SQLALCHEMY_URI = f"sqlite:///{DEFAULT_SQLITE_PATH}"

class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_SQLALCHEMY_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SWAGGER = {"title": "Meus Contatos MS API", "uiversion": 3, "specs_route": "/api/docs"}

    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "dev-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=8)

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False

def get_config():
    env = (os.getenv("FLASK_ENV") or "development").lower()
    return DevConfig if env == "development" else ProdConfig