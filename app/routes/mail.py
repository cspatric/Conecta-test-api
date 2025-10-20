from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from flasgger import swag_from

from app.services.ms_oauth import (
    send_email as graph_send_email,
    list_sent_emails as graph_list_sent,
    graph_get,
)

bp = Blueprint("mail", __name__)

def _get_ms_access_token_from_request() -> str | None:
    """Tenta pegar o access_token do header Authorization; se não, da sessão."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    ms_token = session.get("ms_token") or {}
    return ms_token.get("access_token")


# ================
# ENVIAR E-MAIL
# ================
@bp.post("/mail/send")
@swag_from({
  "summary": "Envia um e-mail em nome do usuário autenticado (Microsoft 365)",
  "tags": ["Mail"],
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
            "subject": {"type": "string"},
            "body_html": {"type": "string"},
            "to": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Lista de emails de destino"
            }
          },
          "required": ["subject", "body_html", "to"]
        },
        "example": {
          "subject": "Hello from API",
          "body_html": "<h1>Olá!</h1><p>Mensagem de teste via Graph.</p>",
          "to": ["alguem@exemplo.com"]
        }
      }
    }
  },
  "responses": {
    "202": {"description": "Solicitação de envio aceita / criada"},
    "400": {"description": "Payload inválido"},
    "401": {"description": "Token ausente ou inválido"},
    "502": {"description": "Falha ao enviar via Graph"}
  }
})
def send_mail():
    """
    Envia e-mail usando /me/sendMail.
    Requer escopo: Mail.Send (já presente no seu .env).
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({"error": "ms_not_authenticated",
                        "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."}), 401

    body = request.get_json(silent=True) or {}
    subject = (body.get("subject") or "").strip()
    body_html = body.get("body_html") or ""
    to = body.get("to") or []

    if not subject or not isinstance(to, list) or len(to) == 0:
        return jsonify({"error": "validation_error",
                        "message": "Campos obrigatórios: subject, body_html, to (array com pelo menos 1 email)."}), 400

    try:
        res = graph_send_email(access_token, subject=subject, body_html=body_html, to_recipients=to)
        return jsonify(res), 202
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({"error": "ms_token_invalid_or_expired",
                            "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."}), 401
        return jsonify({"error": "graph_error",
                        "message": "Falha ao enviar e-mail via Microsoft Graph.",
                        "detail": msg}), 502


# =======================
# RECEBER (INBOX) E-MAILS
# =======================
@bp.get("/mail/inbox")
@swag_from({
  "summary": "Lista e-mails da caixa de entrada (Inbox) do usuário",
  "tags": ["Mail"],
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
      "schema": {"type": "integer", "default": 25, "minimum": 1, "maximum": 100},
      "required": False,
      "description": "Quantidade de mensagens (1-100)"
    },
    {
      "in": "query",
      "name": "$select",
      "schema": {"type": "string"},
      "required": False,
      "description": "Campos a retornar (ex: subject,from,receivedDateTime,bodyPreview). Default já cobre os mais úteis."
    }
  ],
  "responses": {
    "200": {"description": "Lista de mensagens da Inbox"},
    "401": {"description": "Token ausente ou inválido"},
    "502": {"description": "Falha ao consultar o Graph"}
  }
})
def list_inbox():
    """
    Lista e-mails da Inbox: /me/mailFolders/Inbox/messages
    Requer escopo: Mail.Read.
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({"error": "ms_not_authenticated",
                        "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."}), 401

    top = request.args.get("top", default=25, type=int) or 25
    select_default = "id,subject,from,receivedDateTime,bodyPreview,toRecipients,isRead,webLink"
    select_param = request.args.get("$select", select_default)

    try:
        data = graph_get(
            "/me/mailFolders/Inbox/messages",
            access_token,
            params={"$top": str(top), "$select": select_param, "$orderby": "receivedDateTime desc"}
        )
        return jsonify(data), 200
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({"error": "ms_token_invalid_or_expired",
                            "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."}), 401
        return jsonify({"error": "graph_error",
                        "message": "Falha ao consultar mensagens na Inbox.",
                        "detail": msg}), 502


# =======================
# ENVIADOS (SENT) E-MAILS
# =======================
@bp.get("/mail/sent")
@swag_from({
  "summary": "Lista e-mails da pasta Enviados (Sent Items) do usuário",
  "tags": ["Mail"],
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
      "schema": {"type": "integer", "default": 25, "minimum": 1, "maximum": 100},
      "required": False,
      "description": "Quantidade de mensagens (1-100)"
    }
  ],
  "responses": {
    "200": {"description": "Lista de mensagens enviadas"},
    "401": {"description": "Token ausente ou inválido"},
    "502": {"description": "Falha ao consultar o Graph"}
  }
})
def list_sent():
    """
    Lista e-mails em /me/mailFolders/SentItems/messages
    Requer escopo: Mail.Read (ou ao menos leitura da pasta).
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({"error": "ms_not_authenticated",
                        "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."}), 401

    top = request.args.get("top", default=25, type=int) or 25
    try:
        data = graph_list_sent_emails(access_token, top=top)
        return jsonify(data), 200
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({"error": "ms_token_invalid_or_expired",
                            "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."}), 401
        return jsonify({"error": "graph_error",
                        "message": "Falha ao consultar mensagens enviadas.",
                        "detail": msg}), 502


# ==========================
# DETALHE DE UMA MENSAGEM
# ==========================
@bp.get("/mail/messages/<message_id>")
@swag_from({
  "summary": "Detalhes de uma mensagem (com body opcional)",
  "tags": ["Mail"],
  "parameters": [
    {"in": "path", "name": "message_id", "schema": {"type": "string"}, "required": True},
    {
      "in": "header",
      "name": "Authorization",
      "schema": {"type": "string"},
      "required": False,
      "description": "Access Token do Microsoft Graph (Bearer <token>)"
    },
    {
      "in": "query",
      "name": "include_body",
      "schema": {"type": "boolean", "default": False},
      "required": False,
      "description": "Se true, inclui body (HTML) além do bodyPreview."
    }
  ],
  "responses": {
    "200": {"description": "Mensagem encontrada"},
    "401": {"description": "Token ausente ou inválido"},
    "404": {"description": "Mensagem não encontrada"},
    "502": {"description": "Falha ao consultar o Graph"}
  }
})
def get_message_detail(message_id: str):
    """
    Retorna detalhes de /me/messages/{id}. Use include_body=true para trazer body.content (HTML).
    """
    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({"error": "ms_not_authenticated",
                        "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."}), 401

    include_body = str(request.args.get("include_body", "false")).lower() in ("1", "true", "yes", "y")
    select_fields = [
        "id","subject","from","sender","toRecipients","ccRecipients","bccRecipients",
        "replyTo","conversationId","receivedDateTime","sentDateTime","isRead",
        "bodyPreview","webLink"
    ]
    if include_body:
        select_fields.append("body")

    try:
        data = graph_get(
            f"/me/messages/{message_id}",
            access_token,
            params={"$select": ",".join(select_fields)}
        )
        return jsonify(data), 200
    except Exception as e:
        msg = str(e)
        if "404" in msg or "Not Found" in msg:
            return jsonify({"error": "not_found", "message": f"Mensagem {message_id} não encontrada."}), 404
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({"error": "ms_token_invalid_or_expired",
                            "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."}), 401
        return jsonify({"error": "graph_error",
                        "message": "Falha ao consultar mensagem no Microsoft Graph.",
                        "detail": msg}), 502