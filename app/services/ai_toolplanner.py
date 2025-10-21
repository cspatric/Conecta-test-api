from __future__ import annotations
import json
from typing import Any, Dict
from app.services.ai_chat import ai_chat
from app.services.ai_validation import validate_ai_action

TOOLS_JSON = """
{
  "tools": [
    {
      "action": "chat_reply",
      "params": {
        "tone": { "type": "string", "optional": true, "default": "friendly" }
      },
      "description": "Responde de forma conversacional sem executar nenhuma ação externa."
    },
    {
      "action": "list_contacts",
      "params": {
        "top": { "type": "integer", "optional": true, "default": 100 },
        "domain": { "type": "string",  "optional": true },
        "query": { "type": "string",   "optional": true }
      },
      "description": "Lista contatos. Pode filtrar por domínio (e.g. gmail.com) e/ou pesquisa por nome/email com 'query'."
    },
    {
      "action": "get_contact",
      "params": {
        "contact_id": { "type": "string", "optional": false }
      },
      "description": "Detalhes de um contato por ID."
    },
    {
      "action": "create_contact",
      "params": {
        "givenName":      { "type": "string",       "optional": false },
        "surname":        { "type": "string",       "optional": true },
        "email":          { "type": "string",       "optional": true },
        "businessPhones": { "type": "array_string", "optional": true },
        "extra":          { "type": "object",       "optional": true }
      },
      "description": "Cria um contato."
    },
    {
      "action": "list_inbox",
      "params": {
        "top": { "type": "integer", "optional": true, "default": 25 }
      },
      "description": "Lista emails da Inbox."
    },
    {
      "action": "list_sent",
      "params": {
        "top": { "type": "integer", "optional": true, "default": 25 }
      },
      "description": "Lista emails enviados."
    },
    {
      "action": "get_message_detail",
      "params": {
        "message_id":   { "type": "string",  "optional": false },
        "include_body": { "type": "boolean", "optional": true, "default": false }
      },
      "description": "Detalhes de um e-mail por ID. Se include_body=true, inclui body HTML."
    },
    {
      "action": "send_mail",
      "params": {
        "subject":   { "type": "string",       "optional": false },
        "body_html": { "type": "string",       "optional": false },
        "to":        { "type": "array_string", "optional": false }
      },
      "description": "Envia um email."
    }
  ],
  "output_format": {
    "type": "object",
    "properties": {
      "action": "string (uma das ações listadas em tools.action)",
      "params": "object (parâmetros válidos conforme a ação escolhida)",
      "reason": "string curta explicando o porquê da escolha",
      "confidence": "number 0..1 (confiança da escolha)",
      "message": "string (resposta conversacional para o usuário, no mesmo idioma do pedido)",
      "message_type": "string (um dos: small_talk, text, contacts_list, contact_detail, email_list, email_detail, email_sent, system, error)"
    },
    "required": ["action", "params", "reason", "confidence", "message", "message_type"]
  }
}
"""

EXAMPLES = """
Exemplo (saudação):
{
  "action": "chat_reply",
  "params": { "tone": "friendly" },
  "reason": "Usuário apenas cumprimentou",
  "confidence": 0.8,
  "message": "Opa, tudo ótimo por aqui! E você, firme? Posso te ajudar em algo agora?",
  "message_type": "small_talk"
}

Exemplo (listar contatos por domínio):
{
  "action": "list_contacts",
  "params": { "domain": "gmail.com", "top": 100 },
  "reason": "Usuário pediu contatos com domínio gmail.com",
  "confidence": 0.9,
  "message": "Beleza! Vou listar seus contatos do domínio gmail.com. Quer filtrar por nome também?",
  "message_type": "contacts_list"
}

Exemplo (listar inbox):
{
  "action": "list_inbox",
  "params": { "top": 10 },
  "reason": "Usuário quer os e-mails mais recentes da Inbox",
  "confidence": 0.85,
  "message": "Certo! Vou buscar os 10 e-mails mais recentes da sua caixa de entrada.",
  "message_type": "email_list"
}

Exemplo (listar enviados):
{
  "action": "list_sent",
  "params": { "top": 10 },
  "reason": "Usuário quer os e-mails mais recentes enviados",
  "confidence": 0.84,
  "message": "Ok! Vou listar os 10 e-mails mais recentes da pasta Enviados.",
  "message_type": "email_list"
}

Exemplo (detalhe de e-mail):
{
  "action": "get_message_detail",
  "params": { "message_id": "AAMkADk...AAA=", "include_body": true },
  "reason": "Usuário quer abrir um e-mail específico",
  "confidence": 0.84,
  "message": "Abrindo os detalhes dessa mensagem.",
  "message_type": "email_detail"
}

Exemplo (enviar email):
{
  "action": "send_mail",
  "params": {
    "subject": "Atualização do projeto",
    "body_html": "<p>Segue atualização...</p>",
    "to": ["alguem@exemplo.com"]
  },
  "reason": "Usuário pediu para enviar um email",
  "confidence": 0.87,
  "message": "Show! Preparando o envio com o assunto 'Atualização do projeto'. Quer incluir alguém em cópia?",
  "message_type": "email_sent"
}
"""

SYSTEM_INSTRUCTIONS = """
Você é um planejador de chamadas de API + assistente conversacional.
Responda APENAS com JSON em conformidade com 'output_format' do CATÁLOGO.
REGRAS:
- SEMPRE inclua 'message' e 'message_type'.
- 'message_type' deve ser um dos: small_talk, text, contacts_list, contact_detail, email_list, email_detail, email_sent, system, error.
- Se o usuário apenas conversar (saudação, agradecimento, papo informal), use a ação 'chat_reply' e 'message_type' = 'small_talk'.
- Se houver uma ação concreta, escolha a ação correta e escreva 'message' explicando resumidamente o que será feito/feito.
- Use ESTRITAMENTE os parâmetros definidos na ação escolhida; não invente campos ou chaves fora do catálogo.
- Responda no MESMO IDIOMA do usuário.
- Saída: JSON puro (sem markdown, sem cercas de código).
"""

def _strip_code_fences(s: str) -> str:
  t = s.strip()
  if t.startswith("```"):
      t = t[3:].strip()
      if t.lower().startswith("json"):
          t = t[4:].strip()
      if t.endswith("```"):
          t = t[:-3].strip()
  return t

def plan_action(user_prompt: str) -> Dict[str, Any]:
  prompt = (
      SYSTEM_INSTRUCTIONS
      + "\n\nCATÁLOGO DE FERRAMENTAS E FORMATO DE SAÍDA:\n"
      + TOOLS_JSON
      + "\n\nEXEMPLOS:\n"
      + EXAMPLES
      + "\n\nPEDIDO DO USUÁRIO:\n"
      + user_prompt
      + "\n\nResponda apenas com o JSON exigido pelo 'output_format'."
  )

  raw = ai_chat(prompt)
  text = _strip_code_fences(raw)

  try:
      plan = json.loads(text)
  except json.JSONDecodeError:
      return {
          "action": "chat_reply",
          "params": { "tone": "friendly" },
          "reason": "Falha ao decodificar JSON do modelo",
          "confidence": 0.4,
          "message": "Recebi sua mensagem, mas tive um deslize no parser. Pode repetir em uma frase curta o que você quer que eu faça?",
          "message_type": "error"
      }

  validation = validate_ai_action(plan, raw)
  if not validation.get("valid", False):
      return {
          "action": "chat_reply",
          "params": { "tone": "friendly" },
          "reason": f"Plano inválido: {validation.get('message','sem detalhes')}",
          "confidence": 0.4,
          "message": "Beleza, mas algo não bateu aqui no plano. Quer me dizer de novo o que precisa, tipo: 'listar inbox 10 últimos'?",
          "message_type": "error"
      }

  clean = validation["clean"]

  if not isinstance(clean.get("message"), str) or not clean["message"].strip():
      clean["message"] = "Tudo certo! Vou executar essa ação. Se quiser ajustar algum parâmetro, me fala."
  if clean.get("message_type") not in {
      "small_talk","text","contacts_list","contact_detail",
      "email_list","email_detail","email_sent","system","error"
  }:
      mapping = {
          "chat_reply": "text",
          "list_contacts": "contacts_list",
          "get_contact": "contact_detail",
          "create_contact": "contact_detail",
          "list_inbox": "email_list",
          "list_sent": "email_list",
          "get_message_detail": "email_detail",
          "send_mail": "email_sent"
      }
      clean["message_type"] = mapping.get(clean.get("action","chat_reply"), "text")

  return clean