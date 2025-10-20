from __future__ import annotations
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from app.services.ai_chat import ai_chat

bp = Blueprint("ai", __name__)

@bp.post("/chat")
@swag_from({
  "summary": "Envia uma mensagem de texto para a IA Gemini e retorna a resposta",
  "tags": ["AI"],
  "requestBody": {
    "required": True,
    "content": {
      "application/json": {
        "schema": {
          "type": "object",
          "properties": {
            "prompt": {"type": "string", "description": "Mensagem ou instrução a ser enviada para a IA"}
          },
          "required": ["prompt"]
        },
        "example": {"prompt": "Explique o que é OAuth2 em português simples."}
      }
    }
  },
  "responses": {
    "200": {"description": "Resposta gerada"},
    "400": {"description": "Prompt ausente ou inválido"},
    "500": {"description": "Erro interno ao comunicar com a IA"}
  }
})
def chat_with_ai():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "validation_error", "message": "Campo 'prompt' é obrigatório."}), 400

    try:
        resposta = ai_chat(prompt)
        return jsonify({"response": resposta}), 200
    except Exception as e:
        return jsonify({"error": "ai_chat_failed", "message": f"Falha ao gerar resposta da IA: {str(e)}"}), 500