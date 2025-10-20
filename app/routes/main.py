from .contacts import bp as contacts_bp
from .auth import bp as auth_ms_bp
from .auth_local import bp as auth_local_bp

def register_routes(app):
    """Registra todas as rotas principais da aplicação."""
    app.register_blueprint(auth_ms_bp)
    app.register_blueprint(auth_local_bp)
    app.register_blueprint(contacts_bp, url_prefix="/api")