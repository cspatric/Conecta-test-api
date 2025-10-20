# app/routes/contacts.py
from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from flasgger import swag_from

from app.services.ms_oauth import (
    fetch_contacts_grouped_by_domain,
    create_contact as graph_create_contact,
    graph_get,
)

bp = Blueprint("contacts", __name__)

def _get_ms_access_token_from_request() -> str | None:
    """Tenta pegar o access_token do header Authorization; se não, da sessão."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    ms_token = session.get("ms_token") or {}
    return ms_token.get("access_token")


@bp.get("/contacts")
@swag_from({
  "summary": "Lista contatos do Microsoft 365 agrupados por domínio",
  "tags": ["Contacts"],
  "parameters": [
    {
      "in": "header",
      "name": "Authorization",
      "schema": {"type": "string"},
      "required": False,
      "description": "Access Token do Microsoft Graph (Bearer <token>)"
    },
    {
      "in": "query",
      "name": "top",
      "schema": {"type": "integer", "default": 100, "minimum": 1, "maximum": 999},
      "required": False,
      "description": "Quantidade máxima de contatos a retornar do Graph (default 100)"
    }
  ],
  "responses": {
    "200": {"description": "Mapa domínio → lista de contatos"},
    "401": {"description": "Token ausente ou inválido"},
    "502": {"description": "Falha ao consultar o Microsoft Graph"}
  }
})
def list_contacts():
    """
    Lê contatos do Graph usando Authorization: Bearer <token> (preferência)
    ou o token salvo em session['ms_token'] (fallback).
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({
            "error": "ms_not_authenticated",
            "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."
        }), 401

    top = request.args.get("top", default=100, type=int) or 100
    try:
        data = fetch_contacts_grouped_by_domain(access_token, top=top)
        return jsonify(data)
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({
                "error": "ms_token_invalid_or_expired",
                "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."
            }), 401
        return jsonify({
            "error": "graph_error",
            "message": "Falha ao consultar o Microsoft Graph.",
            "detail": msg
        }), 502


@bp.post("/contacts")
@swag_from({
  "summary": "Cria um contato na pasta padrão do usuário",
  "tags": ["Contacts"],
  "parameters": [
    {
      "in": "header",
      "name": "Authorization",
      "schema": {"type": "string"},
      "required": False,
      "description": "Access Token do Microsoft Graph (Bearer <token>)"
    }
  ],
  "requestBody": {
    "required": True,
    "content": {
      "application/json": {
        "schema": {
          "type": "object",
          "properties": {
            "givenName": {"type": "string"},
            "surname": {"type": "string"},
            "email": {"type": "string"},
            "businessPhones": {"type": "array", "items": {"type": "string"}},
            "extra": {"type": "object"}
          },
          "required": ["givenName"]
        },
        "example": {
          "givenName": "Fulano",
          "surname": "da Silva",
          "email": "fulano@exemplo.com",
          "businessPhones": ["+55 11 99999-0000"],
          "extra": {
            "companyName": "Conecta",
            "jobTitle": "Dev"
          }
        }
      }
    }
  },
  "responses": {
    "201": {"description": "Contato criado", "content": {"application/json": {}}},
    "400": {"description": "Payload inválido"},
    "401": {"description": "Token ausente ou inválido"},
    "502": {"description": "Falha ao criar no Microsoft Graph"}
  }
})
def create_contact():
    """
    Cria um contato em /me/contacts (pasta padrão).
    Requer escopo: Contacts.ReadWrite.
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({
            "error": "ms_not_authenticated",
            "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."
        }), 401

    body = request.get_json(silent=True) or {}
    givenName = (body.get("givenName") or "").strip()
    surname = (body.get("surname") or None)
    email = (body.get("email") or None)
    businessPhones = body.get("businessPhones") or None
    extra = body.get("extra") or None

    if not givenName:
        return jsonify({"error": "validation_error", "message": "Campo 'givenName' é obrigatório."}), 400

    try:
        created = graph_create_contact(
            access_token=access_token,
            givenName=givenName,
            surname=surname,
            email=email,
            businessPhones=businessPhones,
            extra=extra,
        )
        return jsonify(created), 201
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({
                "error": "ms_token_invalid_or_expired",
                "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."
            }), 401
        return jsonify({
            "error": "graph_error",
            "message": "Falha ao criar contato no Microsoft Graph.",
            "detail": msg
        }), 502


@bp.get("/contacts/<contact_id>")
@swag_from({
  "summary": "Detalhes de um contato do Microsoft 365",
  "tags": ["Contacts"],
  "parameters": [
    {
      "in": "path",
      "name": "contact_id",
      "schema": {"type": "string"},
      "required": True,
      "description": "ID do contato no Microsoft Graph (/me/contacts/{id})"
    },
    {
      "in": "header",
      "name": "Authorization",
      "schema": {"type": "string"},
      "required": False,
      "description": "Access Token do Microsoft Graph (Bearer <token>)"
    },
    {
      "in": "query",
      "name": "$select",
      "schema": {"type": "string"},
      "required": False,
      "description": "Campos a retornar (ex: displayName,emailAddresses,companyName). Se não enviar, uso um conjunto padrão."
    }
  ],
  "responses": {
    "200": {"description": "Contato encontrado"},
    "401": {"description": "Token ausente ou inválido"},
    "404": {"description": "Contato não encontrado"},
    "502": {"description": "Falha ao consultar o Microsoft Graph"}
  }
})
def get_contact_details(contact_id: str):
    """
    Retorna detalhes do contato /me/contacts/{id}.
    Usa Authorization: Bearer <token> ou token salvo na sessão.
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({
            "error": "ms_not_authenticated",
            "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."
        }), 401

    # Campos padrão bem completos; pode customizar via query $select
    default_select = ",".join([
        "id","displayName","givenName","surname",
        "emailAddresses","businessPhones","homePhones","mobilePhone",
        "companyName","jobTitle","department","officeLocation",
        "imAddresses","birthday","personalNotes","categories",
        "createdDateTime","lastModifiedDateTime"
    ])
    select_param = request.args.get("$select", default_select)

    try:
        data = graph_get(
            f"/me/contacts/{contact_id}",
            access_token,
            params={"$select": select_param}
        )
        return jsonify(data), 200

    except Exception as e:
        msg = str(e)
        if "404" in msg or "Not Found" in msg:
            return jsonify({
                "error": "not_found",
                "message": f"Contato {contact_id} não encontrado."
            }), 404

        if "401" in msg or "Unauthorized" in msg:
            return jsonify({
                "error": "ms_token_invalid_or_expired",
                "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."
            }), 401

        return jsonify({
            "error": "graph_error",
            "message": "Falha ao consultar o Microsoft Graph.",
            "detail": msg
        }), 502