# app/main.py
from flask import Flask, jsonify
from flasgger import Swagger

from .extensions import db, migrate, cors, jwt
from .config import get_config
from .swagger.base_spec import base_spec

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    cors(app, resources={r"/api/*": {"origins": "*"}})
    jwt.init_app(app)

    from .models import user

    from .routes.main import register_routes
    register_routes(app)

    app.config["SWAGGER"] = {
        "title": "Meus Contatos MS API",
        "uiversion": 3,
        "specs_route": "/api/docs",
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec_1",
                "route": "/api/docs.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs",
    }

    Swagger(app, template=base_spec, config=swagger_config)

    @app.get("/api/health")
    def health():
        """
        Health check
        ---
        tags:
          - Health
        responses:
          200:
            description: ok
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
        """
        return jsonify({"status": "ok"})

    return app