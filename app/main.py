from flask import Flask
from flasgger import Swagger

from .extensions import db, migrate, cors
from .config import get_config
from .swagger.base_spec import base_spec

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    cors(app, resources={r"/api/*": {"origins": "*"}})

    Swagger(app, template=base_spec)

    from .models import user

    from .routes.main import register_routes
    register_routes(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app