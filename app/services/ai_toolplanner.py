from __future__ import annotations
import json
from typing import Any, Dict
from app.services.ai_chat import ai_chat
from app.services.ai_validation import validate_ai_action

TOOLS_JSON = """
{
  "tools": [
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
      "action": "string (uma das ações listadas)",
      "params": "object (parâmetros da ação)",
      "reason": "string curta explicando o porquê",
      "confidence": "number 0..1"
    }
  }
}
"""

EXAMPLES = """
Exemplo 1 (listar todos os contatos):
{
  "action": "list_contacts",
  "params": { "top": 100 },
  "reason": "Usuário pediu todos os contatos",
  "confidence": 0.86
}

Exemplo 2 (listar contatos por domínio):
{
  "action": "list_contacts",
  "params": { "domain": "gmail.com", "top": 100 },
  "reason": "Usuário pediu contatos com domínio gmail.com",
  "confidence": 0.88
}

Exemplo 3 (buscar contato por nome):
{
  "action": "list_contacts",
  "params": { "query": "patrick", "top": 100 },
  "reason": "Usuário quer encontrar Patrick",
  "confidence": 0.83
}

Exemplo 4 (detalhes de um contato):
{
  "action": "get_contact",
  "params": { "contact_id": "AAMkADk...AAA=" },
  "reason": "Usuário quer detalhes por ID",
  "confidence": 0.84
}

Exemplo 5 (enviar email):
{
  "action": "send_mail",
  "params": {
    "subject": "Atualização do projeto",
    "body_html": "<p>Segue atualização...</p>",
    "to": ["alguem@exemplo.com"]
  },
  "reason": "Usuário pediu para enviar um email",
  "confidence": 0.87
}

Exemplo 6 (listar inbox):
{
  "action": "list_inbox",
  "params": { "top": 10 },
  "reason": "Usuário quer os e-mails mais recentes da Inbox",
  "confidence": 0.82
}

Exemplo 7 (listar enviados):
{
  "action": "list_sent",
  "params": { "top": 20 },
  "reason": "Usuário quer ver enviados",
  "confidence": 0.81
}
"""

SYSTEM_INSTRUCTIONS = """
Você é um planejador de chamadas de API. Dado o pedido do usuário, escolha UMA ação válida e gere APENAS um JSON no formato exigido.
Regras:
- Use estritamente uma das ações do catálogo.
- Preencha somente os parâmetros dessa ação.
- Não invente campos.
- Responda apenas com JSON puro (sem markdown, sem ```).
- Se a intenção não estiver relacionada, ainda assim selecione a ação mais próxima (em geral list_contacts com query), mas mantenha 'confidence' baixo.
"""

def _strip_code_fences(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    return t.strip()

def plan_action(user_prompt: str) -> Dict[str, Any]:
    prompt = (
        SYSTEM_INSTRUCTIONS
        + "\n\nCATÁLOGO DE FERRAMENTAS:\n"
        + TOOLS_JSON
        + "\n\nEXEMPLOS:\n"
        + EXAMPLES
        + "\n\nPEDIDO DO USUÁRIO:\n"
        + user_prompt
        + "\n\nResponda apenas com o JSON no formato do catálogo."
    )
    raw = ai_chat(prompt)
    text = _strip_code_fences(raw)
    plan = json.loads(text)

    validation = validate_ai_action(plan, raw)
    if not validation.get("valid", False):
        raise ValueError(f"Plano inválido: {validation.get('message','sem detalhes')}")

    return validation["clean"]