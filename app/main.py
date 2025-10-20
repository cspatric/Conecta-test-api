# app/main.py
import os
from flask import Flask, jsonify
from flasgger import Swagger
from flask_cors import CORS
from .config import get_config
from .swagger.base_spec import base_spec


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # ========= Sessão =========
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    # ========= CORS =========
    # permite chamadas do front local
    FRONT_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    CORS(app, resources={
        r"/api/*": {"origins": FRONT_ORIGINS, "supports_credentials": True},
        r"/auth/*": {"origins": FRONT_ORIGINS, "supports_credentials": True},
    })

    # ========= Permitir HTTPS falso (em dev) =========
    if os.getenv("FLASK_ENV") == "development":
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
        app.config.setdefault("SESSION_COOKIE_SECURE", False)

    # ========= Rotas =========
    from .routes.main import register_routes
    register_routes(app)

    # ========= Swagger =========
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

    # ========= Healthcheck =========
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