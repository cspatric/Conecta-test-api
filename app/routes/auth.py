from __future__ import annotations

from flask import Blueprint, redirect, request, session, jsonify
from ..services.ms_oauth import build_auth_url, fetch_token_by_code, call_graph

bp = Blueprint("auth", __name__)

@bp.get("/auth/login")
def login():
    """
    Inicia login com Microsoft (OAuth 2.0)
    ---
    tags:
      - Auth (Microsoft)
    responses:
      302:
        description: Redireciona para a tela de login da Microsoft
    """
    auth_url, oauth_state = build_auth_url()
    session["oauth_state"] = oauth_state
    return redirect(auth_url)


@bp.get("/auth/callback")
def callback():
    """
    Callback do OAuth Microsoft
    ---
    tags:
      - Auth (Microsoft)
    parameters:
      - in: query
        name: code
        schema: { type: string }
        description: Authorization code retornado pela Microsoft
      - in: query
        name: state
        schema: { type: string }
        description: Valor de state para validação CSRF
      - in: query
        name: error
        schema: { type: string }
        description: Código de erro retornado pela Microsoft, se houver
      - in: query
        name: error_description
        schema: { type: string }
        description: Descrição do erro
    responses:
      200:
        description: Retorna o access_token da Microsoft e os dados do usuário (/me)
      400:
        description: Erro de validação/fluxo OAuth
    """
    sent_state = request.args.get("state")
    saved_state = session.get("oauth_state")
    if not saved_state or sent_state != saved_state:
        return jsonify({
            "error": "invalid_state",
            "sent_state": sent_state,
            "saved_state": saved_state
        }), 400

    if request.args.get("error"):
        return jsonify({
            "error": request.args.get("error"),
            "desc": request.args.get("error_description")
        }), 400

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing_code"}), 400

    try:
        token = fetch_token_by_code(code, saved_state)
    except Exception as e:
        return jsonify({"error": "token_exchange_failed", "exc": str(e)}), 400

    access_token = token.get("access_token")
    if not access_token:
        return jsonify({"auth_error": token}), 400

    session["ms_token"] = token
    session.pop("oauth_state", None)

    try:
        me = call_graph("/me", access_token)
    except Exception as e:
        me = {"error_fetching_me": str(e)}

    return jsonify({
        "ms_access_token": access_token,
        "token": {
            "token_type": token.get("token_type"),
            "expires_in": token.get("expires_in"),
            "expires_at": token.get("expires_at"),

        },
        "me": me
    })


@bp.post("/auth/logout")
def logout():
    """
    Logout (limpa sessão Microsoft)
    ---
    tags:
      - Auth (Microsoft)
    responses:
      200:
        description: Sessão limpa
        content:
          application/json:
            schema:
              type: object
              properties:
                ok:
                  type: boolean
                  example: true
    """
    session.pop("ms_token", None)
    session.pop("oauth_state", None)
    return jsonify({"ok": True})