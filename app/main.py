import os
from flask import Flask, jsonify
from flasgger import Swagger
from flask_cors import CORS
from .config import get_config
from .swagger.base_spec import base_spec
from .extensions import db, migrate
from .middleware.request_logger import register_request_hooks
from .models import request_log


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    db.init_app(app)
    migrate.init_app(app, db)

    FRONT_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    CORS(
        app,
        supports_credentials=True,
        resources={r"/*": {"origins": FRONT_ORIGINS}},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Type", "Authorization"],
    )

    if os.getenv("FLASK_ENV") == "development":
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
        app.config.setdefault("SESSION_COOKIE_SECURE", False)

    from .routes.main import register_routes
    register_routes(app)
    register_request_hooks(app)

    app.config["SWAGGER"] = {
        "title": "Conecta API - Microsoft Contacts",
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
        return jsonify({"status": "ok"})

    return app