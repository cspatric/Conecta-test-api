from .contacts import bp as contacts_bp
from .mail import bp as mail_bp
from .auth import bp as auth_ms_bp


def register_routes(app):
    """Registra todas as rotas principais da aplicação (apenas Microsoft)."""
    app.register_blueprint(auth_ms_bp)                    # /auth/login, /auth/callback, /auth/logout
    app.register_blueprint(contacts_bp, url_prefix="/api")
    app.register_blueprint(mail_bp, url_prefix="/api")