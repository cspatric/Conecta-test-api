from flask import Blueprint, jsonify
from flasgger import swag_from

bp = Blueprint("contacts", __name__)

@bp.get("/contacts")
@swag_from({
  "summary": "Lista contatos agrupados por domínio (mock)",
  "tags": ["Contacts"],
  "responses": {
    "200": {
      "description": "Mapa domínio → lista de contatos",
      "content": {
        "application/json": {
          "example": {
            "conectasuite.com": [
              {"displayName": "TI Conecta", "email": "ti@conectasuite.com"}
            ],
            "gmail.com": [
              {"displayName": "Patrick", "email": "patrick@gmail.com"}
            ]
          }
        }
      }
    }
  }
})
def list_contacts():
    data = {
        "conectasuite.com": [{"displayName": "TI Conecta", "email": "ti@conectasuite.com"}],
        "gmail.com": [{"displayName": "Patrick", "email": "patrick@gmail.com"}],
    }
    return jsonify(data)