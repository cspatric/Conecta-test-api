from .contacts import bp as contacts_bp

def register_routes(app):
    """Registra todas as rotas principais da aplicação."""
    app.register_blueprint(contacts_bp, url_prefix="/api")