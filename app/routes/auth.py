from __future__ import annotations

from flask import Blueprint, redirect, request, session, jsonify
from app.services.ms_oauth import build_auth_url, fetch_token_by_code, call_graph

bp = Blueprint("auth", __name__)

@bp.get("/login")
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


@bp.get("/callback")
def callback():
    import json, base64, urllib.parse 

    sent_state = request.args.get("state")
    saved_state = session.get("oauth_state")
    if not saved_state or sent_state != saved_state:
        return redirect("http://localhost:5173/login?err=state")

    if request.args.get("error"):
        e = request.args.get("error")
        d = request.args.get("error_description", "")
        return redirect(f"http://localhost:5173/login?err={e}&desc={d}")

    code = request.args.get("code")
    if not code:
        return redirect("http://localhost:5173/login?err=missing_code")

    try:
        token = fetch_token_by_code(code, saved_state)
    except Exception as e:
        return redirect(f"http://localhost:5173/login?err=token_exchange_failed&desc={e}")

    access_token = token.get("access_token")
    if not access_token:
        return redirect("http://localhost:5173/login?err=no_access_token")

    session.pop("oauth_state", None)
    session["ms_token"] = token

    try:
        me = call_graph("/me", access_token)
    except Exception as e:
        me = {"error_fetching_me": str(e)}

    session["user"] = {
        "id": me.get("id"),
        "displayName": me.get("displayName"),
        "userPrincipalName": me.get("userPrincipalName"),
        "mail": me.get("mail"),
    }

    payload = {
        "ms_access_token": access_token,
        "token": {
            "token_type": token.get("token_type"),
            "expires_in": token.get("expires_in"),
            "expires_at": token.get("expires_at"),
        },
        "me": me,
    }

    b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    return redirect(f"http://localhost:5173/home#session={urllib.parse.quote(b64)}", code=302)

@bp.post("/logout")
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