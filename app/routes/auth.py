from flask import Blueprint, redirect, request, session, jsonify
from flask_jwt_extended import create_access_token
from ..extensions import db
from ..models.user import User
from ..services.ms_oauth import build_auth_url, fetch_token_by_code, call_graph

bp = Blueprint("auth", __name__)

@bp.get("/auth/login")
def login():
    """
    Inicia login com Microsoft (OAuth2)
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
        type: string
        required: false
        description: Authorization code retornado pela Microsoft
      - in: query
        name: state
        type: string
        required: false
        description: Valor de state para validação CSRF
      - in: query
        name: error
        type: string
        required: false
        description: Código de erro retornado pela Microsoft, se houver
      - in: query
        name: error_description
        type: string
        required: false
        description: Descrição do erro
    responses:
      200:
        description: Retorna JWT local e dados do usuário
        schema:
          type: object
          properties:
            access_token:
              type: string
            user:
              type: object
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

    me = call_graph("/me", access_token)
    email = (me.get("mail") or me.get("userPrincipalName") or "").lower()
    name = me.get("displayName") or ""
    ms_oid = me.get("id")

    if not email:
        return jsonify({"error": "no_email_from_graph", "me": me}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name or email.split("@")[0], email=email, ms_oid=ms_oid)
        db.session.add(user)
    else:
        user.name = name or user.name
        user.ms_oid = ms_oid or user.ms_oid

    db.session.commit()

    jwt_token = create_access_token(
        identity=user.uuid,
        additional_claims={"email": user.email, "name": user.name}
    )

    return jsonify({"access_token": jwt_token, "user": user.to_dict()})


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
        schema:
          type: object
          properties:
            ok:
              type: boolean
              example: true
    """
    session.pop("ms_token", None)
    return jsonify({"ok": True})