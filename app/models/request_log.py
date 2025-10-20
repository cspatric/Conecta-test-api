from app.extensions import db
from datetime import datetime
import uuid

class RequestLog(db.Model):
    __tablename__ = "request_logs"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    method = db.Column(db.String(10))
    path = db.Column(db.String(255))
    status_code = db.Column(db.Integer)
    ip = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ms_email = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=True)