from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..extensions import db
from ..models.user import User

bp = Blueprint("auth_local", __name__)

@bp.post("/auth/login")
def login_local():
    """
    Login local (email/senha) → JWT
    ---
    tags:
      - Auth (Local)
    parameters:
      - in: body
        name: credentials
        schema:
          type: object
          required: [email, password]
          properties:
            email:
              type: string
              example: user@example.com
            password:
              type: string
              example: "secret123"
    responses:
      200:
        description: Login bem-sucedido
        schema:
          type: object
          properties:
            access_token:
              type: string
              example: eyJ0eXAiOiJKV1QiLCJh...
            user:
              type: object
      400:
        description: Credenciais ausentes
      401:
        description: Credenciais inválidas
    """
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "missing_credentials"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    token = create_access_token(identity=user.uuid, additional_claims={"email": user.email, "name": user.name})
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.post("/auth/set-password")
@jwt_required()
def set_password():
    """
    Define/atualiza senha do usuário autenticado (JWT)
    ---
    tags:
      - Auth (Local)
    security:
      - bearerAuth: []
    parameters:
      - in: body
        name: payload
        schema:
          type: object
          required: [password, password_confirm]
          properties:
            password:
              type: string
              example: "NovaSenha123!"
            password_confirm:
              type: string
              example: "NovaSenha123!"
    responses:
      200:
        description: Senha atualizada
        schema:
          type: object
          properties:
            ok:
              type: boolean
              example: true
      400:
        description: Erro de validação
      401:
        description: Não autenticado
      404:
        description: Usuário não encontrado
    """
    current_uuid = get_jwt_identity()
    user = User.query.filter_by(uuid=current_uuid).first()
    if not user:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json(force=True, silent=True) or {}
    p1 = data.get("password") or ""
    p2 = data.get("password_confirm") or ""
    if not p1 or not p2:
        return jsonify({"error": "missing_password"}), 400

    try:
        user.set_password(p1, p2)
        db.session.commit()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"ok": True})


@bp.get("/auth/me")
@jwt_required()
def me():
    """
    Retorna dados do usuário autenticado (JWT)
    ---
    tags:
      - Auth (Local)
    security:
      - bearerAuth: []
    responses:
      200:
        description: OK
        schema:
          type: object
      401:
        description: Não autenticado
      404:
        description: Usuário não encontrado
    """
    current_uuid = get_jwt_identity()
    user = User.query.filter_by(uuid=current_uuid).first()
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify(user.to_dict())