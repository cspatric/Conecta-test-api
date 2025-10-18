from ..extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120))
    email = db.Column(db.String(180), unique=True, index=True)

    def to_dict(self):
        return {"id": self.id, "display_name": self.display_name, "email": self.email}