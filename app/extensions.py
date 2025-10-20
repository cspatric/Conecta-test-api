from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()

def cors(app, **kwargs):
    """Wrapper opcional para manter a assinatura anterior."""
    return CORS(app, **kwargs)