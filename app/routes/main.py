from .auth import bp as auth_bp
from .contacts import bp as contacts_bp
from .mail import bp as mail_bp


def register_routes(app):
    """Registra todos os blueprints principais da aplicação."""

    # ========= Rotas de autenticação (Microsoft OAuth) =========
    app.register_blueprint(auth_bp, url_prefix="/auth")

    api_prefix = "/api"

    app.register_blueprint(contacts_bp, url_prefix=f"{api_prefix}/contacts")

    app.register_blueprint(mail_bp, url_prefix=f"{api_prefix}/mail")