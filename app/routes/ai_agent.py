from __future__ import annotations
from flask import Blueprint, request, jsonify, session
from flasgger import swag_from
from typing import Any, Dict, List

from app.services.ai_toolplanner import plan_action
from app.services.ms_oauth import (
    graph_get,
    create_contact as graph_create_contact,
    send_email as graph_send_email,
    list_sent_emails as graph_list_sent,
)

bp = Blueprint("ai_agent", __name__)

def _get_ms_access_token_from_request() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    ms_token = session.get("ms_token") or {}
    return ms_token.get("access_token")

def _flatten_contacts(access_token: str, top: int = 200) -> List[Dict[str, Any]]:
    params = {
        "$select": "id,displayName,emailAddresses,businessPhones,mobilePhone,companyName,jobTitle",
        "$top": str(top),
    }
    data = graph_get("/me/contacts", access_token, params=params)
    items = []
    for c in data.get("value", []) or []:
        emails = [e.get("address") for e in (c.get("emailAddresses") or []) if e.get("address")]
        items.append({
            "id": c.get("id"),
            "displayName": c.get("displayName"),
            "emails": emails,
            "businessPhones": c.get("businessPhones") or [],
            "mobilePhone": c.get("mobilePhone"),
            "companyName": c.get("companyName"),
            "jobTitle": c.get("jobTitle"),
        })
    return items

def _filter_by_domain(items: List[Dict[str, Any]], domain: str) -> List[Dict[str, Any]]:
    domain = domain.lower().strip()
    out = []
    for it in items:
        for em in it.get("emails", []):
            if isinstance(em, str) and "@" in em and em.lower().split("@", 1)[1] == domain:
                out.append(it)
                break
    return out

def _filter_by_query(items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    q = query.lower().strip()
    out = []
    for it in items:
        hay = " ".join([it.get("displayName") or ""] + (it.get("emails") or [])).lower()
        if q in hay:
            out.append(it)
    return out

@bp.post("/")
@swag_from({
  "summary": "Planeja e executa ações nos seus endpoints via linguagem natural",
  "tags": ["AI Agent"],
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
          "properties": { "prompt": {"type": "string"} },
          "required": ["prompt"]
        },
        "example": { "prompt": "Liste contatos do domínio gmail.com e procure por 'patrick'." }
      }
    }
  },
  "responses": {
    "200": {"description": "Plano executado com sucesso"},
    "400": {"description": "Entrada inválida"},
    "401": {"description": "Token ausente ou inválido"},
    "502": {"description": "Falha ao consultar serviços externos"}
  }
})
def ai_agent():
    body = request.get_json(silent=True) or {}
    user_prompt = (body.get("prompt") or "").strip()
    if not user_prompt:
        return jsonify({"error": "validation_error", "message": "Campo 'prompt' é obrigatório."}), 400

    access_token = _get_ms_access_token_from_request()
    if not access_token:
        return jsonify({
            "error": "ms_not_authenticated",
            "message": "Forneça Authorization: Bearer <MS_ACCESS_TOKEN> ou faça login em /auth/login."
        }), 401

    try:
        plan = plan_action(user_prompt)
    except Exception as e:
        return jsonify({"error": "planning_failed", "message": str(e)}), 400

    action = plan.get("action")
    params = plan.get("params") or {}

    try:
        if action == "list_contacts":
            top = max(1, min(int(params.get("top") or 100), 999))
            items = _flatten_contacts(access_token, top=top)
            if params.get("domain"):
                items = _filter_by_domain(items, params["domain"])
            if params.get("query"):
                items = _filter_by_query(items, params["query"])
            result = {"count": len(items), "items": items}

        elif action == "get_contact":
            cid = params.get("contact_id")
            if not cid:
                return jsonify({"error": "validation_error", "message": "contact_id é obrigatório."}), 400
            result = graph_get(
                f"/me/contacts/{cid}",
                access_token,
                params={
                    "$select": ",".join([
                        "id","displayName","givenName","surname",
                        "emailAddresses","businessPhones","homePhones","mobilePhone",
                        "companyName","jobTitle","department","officeLocation",
                        "imAddresses","birthday","personalNotes","categories",
                        "createdDateTime","lastModifiedDateTime"
                    ])
                }
            )

        elif action == "create_contact":
            created = graph_create_contact(
                access_token,
                givenName=params.get("givenName"),
                surname=params.get("surname"),
                email=params.get("email"),
                businessPhones=params.get("businessPhones"),
                extra=params.get("extra"),
            )
            result = created

        elif action == "list_inbox":
            top = max(1, min(int(params.get("top") or 25), 100))
            result = graph_get(
                "/me/mailFolders/Inbox/messages",
                access_token,
                params={
                    "$top": str(top),
                    "$select": "id,subject,from,receivedDateTime,bodyPreview,toRecipients,isRead,webLink",
                    "$orderby": "receivedDateTime desc"
                }
            )

        elif action == "list_sent":
            top = max(1, min(int(params.get("top") or 25), 100))
            result = graph_list_sent(access_token, top=top)

        elif action == "send_mail":
            subject = params.get("subject")
            body_html = params.get("body_html")
            to = params.get("to") or []
            if not subject or not body_html or not isinstance(to, list) or not to:
                return jsonify({"error": "validation_error",
                                "message": "subject, body_html e to[] são obrigatórios."}), 400
            result = graph_send_email(access_token, subject=subject, body_html=body_html, to_recipients=to)

        else:
            return jsonify({"error": "unknown_action", "plan": plan}), 400

        return jsonify({"plan": plan, "result": result}), 200

    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({
                "error": "ms_token_invalid_or_expired",
                "message": "Access token Microsoft inválido/expirado. Gere outro em /auth/login."
            }), 401
        return jsonify({"error": "execution_failed", "message": msg, "plan": plan}), 502