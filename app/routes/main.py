from .auth import bp as auth_bp
from .contacts import bp as contacts_bp
from .mail import bp as mail_bp
from .ai import bp as ai_bp
from .ai_agent import bp as ai_agent_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(contacts_bp, url_prefix="/contacts")
    app.register_blueprint(mail_bp, url_prefix="/mail")
    app.register_blueprint(ai_bp, url_prefix="/ai")
    app.register_blueprint(ai_agent_bp, url_prefix="/ai")