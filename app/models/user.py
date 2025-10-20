import uuid
from ..extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    ms_oid = db.Column(db.String(64), nullable=True)

    def set_password(self, password: str, password_confirm: str):
        if password != password_confirm:
            raise ValueError("Passwords do not match")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "name": self.name,
            "email": self.email,
            "has_password": bool(self.password_hash),
            "ms_linked": bool(self.ms_oid),
        }