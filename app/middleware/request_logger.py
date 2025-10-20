from flask import request, g
from app.models.request_log import RequestLog
from app.extensions import db
from datetime import datetime

def register_request_hooks(app):
    @app.after_request
    def log_request(response):
        try:
            log = RequestLog(
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                ip=request.remote_addr,
                ms_email=getattr(g, "ms_email", None),
                message=response.get_data(as_text=True)[:1000],
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return response